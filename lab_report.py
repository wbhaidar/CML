import requests 
#import json
from rich.table import Table
from rich.text import Text
from rich.console import Console
from rich.panel import Panel
import urllib3
import logging


# Log Confg
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Disable HTTPS warnings until Cert is intalled on CML
urllib3.disable_warnings()


##########################
# CONSTANTS
CML_API_VERSION = "/v0"



########################
## HELPER FUNCTIONS

# Helper module to convert Bytes to Largest appropriate unit for readability
def convert_bytes(size):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:3.1f} {x}"
        size /= 1024.0
    return size


# Helper to create headers with authorisation token
def get_headers(auth_token:str) -> dict:
    return {
		'Content-Type': 'application/json',
		'accept': 'application/json',
        'authorization': f"Bearer {auth_token}"
	}

# Handle API requests 
def handle_request(url:str, method = 'get', headers:dict = None, payload:dict = None) -> dict :
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=payload,
            verify=False
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error during request to {url}: {e}")
        return None
    
# Get authentication token
def get_token(url:str, username:str, password:str) -> str:
    api = f"{CML_API_VERSION}/authenticate"

    payload = {
		"username": username,
		"password": password
	}
    return handle_request(f"{url}{api}",method='post', payload=payload)


###########################
## CORE FUNCTIONS

# Fetch all lab details
def fetch_labs(url, auth_token):
    labs={}
    headers = get_headers(auth_token)
    labs_data=handle_request(f"{url}{CML_API_VERSION}/labs?show_all=true", headers=headers)
    if labs_data:
        for lab_id in labs_data:
            lab_details={}
            lab_details= handle_request(f"{url}{CML_API_VERSION}/labs/{lab_id}", headers=headers)
            if lab_details:
                lab_details['lab_nodes']= handle_request(f"{url}{CML_API_VERSION}/labs/{lab_id}/nodes", headers=headers) or {}
                lab_details['lab_links']= handle_request(f"{url}{CML_API_VERSION}/labs/{lab_id}/links", headers=headers) or {}
                labs[lab_id] = lab_details
    return labs
            
# Fetch node details
def fetch_nodes(url, auth_token):
    nodes={}
    headers = get_headers(auth_token)
    nodes_data= handle_request(f"{url}{CML_API_VERSION}/nodes/", headers=headers)
    if nodes_data:
        for n in nodes_data:
            id=n['id']
            nodes[id]=n
        return nodes
    return {}

def fetch_system_stats(url, auth_token):
    headers=get_headers(auth_token)
    licensing=handle_request(f"{url}{CML_API_VERSION}/diagnostics/licensing", headers=headers)
    system_stats=handle_request(f"{url}{CML_API_VERSION}/system_stats", headers=headers)
    return {'licensing': licensing, 'stats': system_stats}


# update nodes struct resource utilisatoin
def update_nodes_with_utilisation(url,auth_token,labs, nodes):
    headers = get_headers(auth_token)

    for lab in labs:
        sim_data = handle_request(f"{url}{CML_API_VERSION}/labs/{lab}/simulation_stats", headers=headers)
        if sim_data and 'nodes' in sim_data: 
            for node_id, stats in sim_data['nodes'].items():
                if node_id in nodes:
                    nodes[node_id]['util']=stats



##########################
## DISPLAY FUNCTIONS

# display a summary of labs
def print_labs_summary(url, labs):
    Console().print(f"[b]Total Topology Labs:[yellow] {str(len(labs))}[/b]")

    table = Table(title=f"Labs on {url}", title_style='bold')
    table.add_column('LabID', justify='left', style='cyan')
    table.add_column('State', justify='left', style='cyan')
    table.add_column('Lab Title', justify='left', style='cyan')
    table.add_column('Owner', justify='left', style='cyan')
    table.add_column('# Nodes', justify='left', style='cyan')
    table.add_column('# Links', justify='left', style='cyan')

    for labid, lab_info in labs.items():
            table.add_row(
                labid, 
                Text(lab_info['state'], style='green' if lab_info['state']=='STARTED' else 'cyan'),
                lab_info['lab_title'],
                lab_info['owner_username'],
                str(lab_info['node_count']),
                str(lab_info['link_count'])
            )
    Console().print()
    Console().print(table)

def print_sys_health(system):
    licensing=system.get('licensing', {})
    stats = system.get('stats',{})

    total_licenses=licensing.get('quota', 0)
    used_licences=licensing.get('started',0)

    Console().print(Panel(f"[b]CML Licenses (Total / Used):[yellow] {total_licenses} / {used_licences}[/b]"))

    table = Table(title=f"Node Health", title_style='bold')
    table.add_column('Hostname', justify='left', style='cyan')
    table.add_column('# CPUs', justify='center', style='cyan')
    table.add_column('CPU Load Avg\n(1min / 5min / 15min)', justify='center', style='cyan')
    table.add_column('Memory\nTotal   /   Free   /   Used %', justify='center', style='cyan')    
    table.add_column('Disk Space\nTotal   /   Free   /   Used %', justify='center', style='cyan')
    
    for compute in stats.get('computes', {}).values():
        mem=compute['stats']['memory']
        mem_used=mem['used']/mem['total']*100
        disk=compute['stats']['disk']
        disk_used=disk['used']/disk['total']*100
        cpu_load=compute['stats']['cpu']['load']
        load=' / '.join(map(str, compute['stats']['cpu']['load']))

        table.add_row(
            compute['hostname'],
            str(compute['stats']['cpu']['count']),
            f"{cpu_load[0]:>6}% {cpu_load[1]:>6}% {cpu_load[2]:>6}%",
            f"{convert_bytes(mem['total']):>10} {convert_bytes(mem['free']):>10} {mem_used:>6.1f}%",
            f"{convert_bytes(disk['total']):>10} {convert_bytes(disk['free']):>10} {disk_used:>6.1f}%"
        )
    Console().print()
    Console().print(table)



# display detailed info about each lab
def print_detailed_lab_info(labs,nodes):

    for labid, lab_info in labs.items():
        table = Table(
            title=f"Lab Detailed Info\n LabID: {labid}\n LabTitle: {labs[labid]['lab_title']}", 
            title_style='bold'
            )
        table.add_column('NodeID', justify='left', style='cyan')
        table.add_column('Label', justify='left', style='cyan')
        table.add_column('Node Definition', justify='left', style='cyan')
        table.add_column('State', justify='left', style='cyan')
        table.add_column('CPU REQ', justify='left', style='cyan')
        table.add_column('RAM REQ', justify='left', style='cyan')
        table.add_column('CPU use', justify='left', style='cyan')
        table.add_column('RAM use', justify='left', style='cyan')

        for node_id in lab_info['lab_nodes']:
            node=nodes[node_id]
            cpu_used=node.get('util', {}).get('cpu_usage', 0.0)
            mem_used=node.get('util', {}).get('ram_usage', 0.0)

            table.add_row(
                node_id,
                node['label'],
                node['node_definition'],
                Text(node['state'], style='green' if node['state']=='BOOTED' else 'cyan'),
                str(node['cpus']),
                str(node['ram']),
                str(cpu_used),
                str(mem_used)
            )
        Console().print()
        Console().print(table)


# export data to json files.
def export_data_to_file(labs={}, nodes={}, system={}):
    import json
    try:
        with open('nodes.json', 'w',encoding='utf-8') as g:
            json.dump(nodes, g, ensure_ascii=False, indent=4)
        with open('labs.json', 'w',encoding='utf-8') as f:
            json.dump(labs, f,ensure_ascii=False, indent=4)
        with open('system.json', 'w',encoding='utf-8') as f:
            json.dump(system, f,ensure_ascii=False, indent=4)            
    except Exception as e:
        logger.error(f"Failed to export JSON data to files. Exception: {e}")


# main function to execute program
def main(server,username,password,export,actions):
    url=f"https://{server}/api"

    auth_token = get_token(url, username, password)

    labs = fetch_labs(url, auth_token) if 'labs' in actions or 'all' in actions else {}
    nodes = fetch_nodes(url, auth_token) if labs else {}
    system = fetch_system_stats(url, auth_token) if 'health' in actions or 'all' in actions else {}


    # print summaries and details
    if 'health' in actions or 'all' in actions:
        print_sys_health(system)
    if 'labs' in actions or 'all' in actions:
        update_nodes_with_utilisation(url, auth_token, labs, nodes)
        print_labs_summary(url, labs)
        print_detailed_lab_info(labs,nodes)

    if export:
        export_data_to_file(labs, nodes, system)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description = "Report on CML Operational State and Usage")
    parser.add_argument('--server', required = True, help='CML Server IP')
    parser.add_argument('--username', required = True, help='CML Username')
    parser.add_argument('--password', required = True, help = 'CML Password')
    parser.add_argument('--export', action='store_true', help = 'Export labs and nodes data to JSON files')
    parser.add_argument('--actions', nargs='+', choices=['health', 'labs', 'all'], default=['all'],
                        help="Specify the action to perform: 'health' for compute node healt, 'labs' for topology labs, 'all' to print all info")
    args = parser.parse_args()

    main(args.server, args.username, args.password, args.export, args.actions)