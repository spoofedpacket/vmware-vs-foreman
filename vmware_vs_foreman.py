#!/usr/bin/env python

"""
Report on hosts present in VMware, but missing in foreman. Checks are based
on the BIOS UUID of the VM.
"""
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

import argparse
import atexit
import os
import smtplib
import socket
import sys
import requests
import pandas

# VMware python libraries
from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim

def get_vms(args, vmware_user, vmware_pass):
    """
    Scrape VMware. Returns a list of VM BIOS UUIDs and power states.
    """
    try:
        service_instance = connect.SmartConnect(host=args.host,
                                                user=vmware_user,
                                                pwd=vmware_pass,
                                                port=int(args.port))
        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()
        container = content.rootFolder  # starting point to look into
        viewtype = [vim.VirtualMachine]  # object types to look for
        recursive = True  # whether we should look into it recursively
        containerview = content.viewManager.CreateContainerView(
            container, viewtype, recursive)
        children = containerview.view
        vmware_uuid_list = [('uuid', [child.summary.config.uuid for child in children]),
                            ('name', [child.summary.config.name for child in children]),
                            ('powerstate', [child.summary.runtime.powerState
                                            for child in children])]
        return vmware_uuid_list

    except vmodl.MethodFault as error:
        print "Caught vmodl fault : " + error.msg
        return -1

def query_foreman(foreman_api_query):
    """
    Scrape foreman. Returns a dictionary of UUIDs and hostnames, with the UUID as the key.
    """
    req = requests.get(foreman_api_query)
    json_data = req.json()
    extract = json_data['results']
    foreman_uuid_dict = {value['uuid'].lower():
                         key for (key, value) in extract.iteritems()}
    return foreman_uuid_dict

def send_mail(send_from, send_to, subject, text, files=None,
              server="127.0.0.1"):
    """
    Function to send email attachment
    """
    assert isinstance(send_to, list)

    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(text))

    for attachment in files or []:
        with open(attachment, "rb") as filehandle:
            part = MIMEApplication(
                filehandle.read(),
                Name=os.path.basename(attachment)
            )
        # After the file is closed
        part['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(attachment)
        msg.attach(part)


    smtp = smtplib.SMTP(server)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()

def main():
    """
    Main program.
    """
    # Parse variables as command line arguments
    argparser = argparse.ArgumentParser()
    argparser.add_argument('-s', '--host',
                           required=True,
                           action='store',
                           help='VMware vSphere host to connect to')
    argparser.add_argument('-o', '--port',
                           required=False,
                           type=int,
                           default=443,
                           action='store',
                           help='Optional port to connect on')
    argparser.add_argument('-a', '--foreman-api-url',
                           required=True,
                           action='store',
                           help='URL of Foreman API')
    argparser.add_argument('-v', '--verbose',
                           required=False,
                           action='store_true',
                           help='Optional verbose mode. Outputs list of hosts to the console')
    argparser.add_argument('-e', '--email-recipients',
                           required=False,
                           default=None,
                           action='store',
                           help='Optional list of email addresses to send the CSV to')
    argparser.add_argument('-r', '--remove-csv',
                           required=False,
                           default=False,
                           action='store_true',
                           help='Optionally remove the CSV on exit')
    argparser.add_argument('-f', '--output-csv',
                           required=False,
                           default='/tmp/vmware_vs_foreman.csv',
                           action='store',
                           help='Optional path to CSV file (default /tmp/vmware_vs_foreman.csv)')
    args = argparser.parse_args()
    # Get credentials for VMware from environment variables
    vmware_user = os.getenv('VMWARE_USER')
    vmware_pass = os.getenv('VMWARE_PASS')
    if vmware_user is None or vmware_pass is None:
        print "Error: VMWARE_USER or VMWARE_PASS environment variable not set"
        sys.exit(1)
    vmware_uuid_list = get_vms(args, vmware_user, vmware_pass)
    foreman_uuid_dict = query_foreman(args.foreman_api_url)
    # Compose pandas dataframes
    vmware_uuid_df = pandas.DataFrame.from_items(vmware_uuid_list)
    foreman_uuid_df = pandas.DataFrame(foreman_uuid_dict.items(), columns=['uuid', 'name'])
    # Compose a dataframe of uuids listed in VMware, but missing in foreman
    vmware_vs_foreman = vmware_uuid_df[~vmware_uuid_df['uuid'].isin(foreman_uuid_df['uuid'])]
    if args.verbose:
        with pandas.option_context('display.max_rows', None, 'display.max_colwidth', 100):
            print vmware_vs_foreman.to_string(index=False)
    # Write out CSV and email it (if required)
    vmware_vs_foreman.to_csv(args.output_csv,
                             encoding='utf-8',
                             columns=['name', 'powerstate'],
                             index=False)
    if not args.email_recipients is None:
        hostname = socket.getfqdn()
        send_mail("vmware_vs_foreman@" + hostname,
                  args.email_recipients.split(),
                  'VMware vs Foreman CSV',
                  'Here is the current VMware vs Foreman CSV',
                  [args.output_csv])
    # Clean up
    if args.remove_csv:
        os.unlink(args.output_csv)
    return 0

# Default invocation
if __name__ == "__main__":
    main()
