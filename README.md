# CML Virtual Modeling Platform Reporting Tool

This tool is built to assist in managing and monitoring the Cisco Modeling Labs (CML) virtual modeling platform by providing a reporting on virtual lab usage. Intent is to provide capability to view lab and node status, resource utilisation , and topology details. 

## Key Features

- **Authentication**: Authenticates with CML API using username and password.
- **Lab reports**: Retrieve and display lab details, including the number of nodes, links, lab owner and state.
- **Node Resource Monitoring**: Reports CPU and RAM utilisation for active nodes within each Lab.
- **JSON Exports**: Saves lab and node data to JSON files for further analysis if required.

## Usage

TO run the tool, use the following command:

```bash
python lab_report.py --server <CML_SERVER_IP> --username <CML_USERNAME> --password <CML_PASSWORD>
```


## Future Updates

- Dormant lab detection : identify labs that have not been active for a configuration period
- Lab Disk Usage Reporting: Report on disk usage for each lab to provide a view of storage footprint of each lab.
- Top Users by resource consumption: identify who consume the most resources.