Tool to find hosts in VMware that do not exist in foreman

# Usage

## Environment Variables

You must set the credentials for your VMware host as environment variables first:

    export VMWARE_USER="vmware_api_user"
    export VMWARE_PASS="vmware_api_pass"

## Command Line

    usage: vmware_vs_foreman.py [-h] -s HOST [-o PORT] -a FOREMAN_API_URL [-v]
 
    optional arguments:
      -h, --help            show this help message and exit
      -s HOST, --host HOST  VMware vSphere host to connect to
      -o PORT, --port PORT  Optional port to connect on
      -a FOREMAN_API_URL, --foreman-api-url FOREMAN_API_URL
                            URL of Foreman API
      -v, --verbose         Optional verbose mode. Outputs list of hosts to the
                            console
      -e EMAIL_RECIPIENTS, --email-recipients EMAIL_RECIPIENTS
                            Optional list of email addresses to send the CSV to
      -r, --remove-csv      Optionally remove the CSV on exit
      -f OUTPUT_CSV, --output-csv OUTPUT_CSV
                            Optional path to CSV file (default
                            /tmp/vmware_vs_foreman.csv)

# Use Cases

Find all inconsistent hosts, and email the report to ``user@example.com`` and ``otheruser@example.com``. The report will be deleted afterwards. This would be the recommended method for running the tool from cron:

    vmware_vs_foreman.py \ 
        -s "192.168.0.5" \
        -a "http://foreman.example.com/api/v2/fact_values?search=name+%3D+uuid&per_page=500" \
        --email-recipients="user@example.com otheruser@example.com" \
        -r

Output the report to ``/home/user/vmware_vs_foreman.csv``, do not send any email:

    vmware_vs_foreman.py \
        -s "192.168.0.5" \
        -a "http://foreman.example.com/api/v2/fact_values?search=name+%3D+uuid&per_page=500" \
        -f /home/user/vmware_vs_foreman.csv

Output the report to the console in a human-readable format. Delete the report in ``/tmp/vmware_vs_foreman.csv`` afterwards:

    vmware_vs_foreman.py \
        -s "192.168.0.5" \
        -a "http://foreman.example.com/api/v2/fact_values?search=name+%3D+uuid&per_page=500" \
        -v \
        -r

