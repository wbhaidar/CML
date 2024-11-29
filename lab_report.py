import requests 
import json
from rich.table import Table
from rich.text import Text
from rich.console import Console
from rich.panel import Panel
import urllib3
urllib3.disable_warnings()

# constants
CML_API_VERSION = "/v0"

# global vars
labs={}
nodes={}
system={}

# Helper module to convert Bytes to Largest appropriate unit for readability
def convert_bytes(size):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:3.1f} {x}"
        size /= 1024.0
    return size


# Helper to create headers
def get_headers(auth_token):
    return {
		'Content-Type': 'application/json',
		'accept': 'application/json',
        'authorization': f"Bearer {auth_token}"
	}

# Get authentication token
def get_token(url, username, password):
    api = f"{CML_API_VERSION}/authenticate"

    payload = {
		"username": username,
		"password": password
	}

    try:
        response = requests.post(url + api, json=payload, verify=False)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        printf(f"Unable to Get Token. Exception Msg {e}")
        return None

# display a summary of labs
def print_labs_summary(url):
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

def print_sys_health():
    total_licenses=system['licensing']['quota']
    used_licences=system['licensing']['started']
    Console().print(Panel(f"[b]CML Licenses (Total / Used):[yellow] {total_licenses} / {used_licences}[/b]"))

    table = Table(
            title=f"Node Health", 
            title_style='bold'
            )
    table.add_column('Hostname', justify='left', style='cyan')
    table.add_column('# CPUs', justify='center', style='cyan')
    table.add_column('CPU Load Avg\n(1min / 5min / 15min)', justify='center', style='cyan')
    table.add_column('Memory\nTotal   /   Free   /   Used %', justify='center', style='cyan')    
    table.add_column('Disk Space\nTotal   /   Free   /   Used %', justify='center', style='cyan')
    
    for node, detail in system['stats']['computes'].items():
        mem=detail['stats']['memory']
        mem_used=mem['used']/mem['total']*100
        disk=detail['stats']['disk']
        disk_used=disk['used']/disk['total']*100
        cpu_load=detail['stats']['cpu']['load']
        load=' / '.join(map(str, detail['stats']['cpu']['load']))

        table.add_row(
            detail['hostname'],
            str(detail['stats']['cpu']['count']),
            f"{cpu_load[0]:>6}% {cpu_load[1]:>6}% {cpu_load[2]:>6}%",
            f"{convert_bytes(mem['total']):>10} {convert_bytes(mem['free']):>10} {mem_used:>6.1f}%",
            f"{convert_bytes(disk['total']):>10} {convert_bytes(disk['free']):>10} {disk_used:>6.1f}%"
        )
    Console().print()
    Console().print(table)



# display detailed info about each lab
def print_detailed_lab_info():

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

# update nodes struct resource utilisatoin
def update_nodes_resource_util(url,auth_token):
    headers = get_headers(auth_token)

    for lab in labs.keys():
        try:
            sim_data = requests.get(
                f"{url}{CML_API_VERSION}/labs/{lab}/simulation_stats", 
                headers=headers, 
                verify=False).json()
            
            node_sim_data=sim_data.get('nodes', {})
        
            for node, node_info in node_sim_data.items():
                    nodes[node]['util']=node_info
        except requests.RequestException as e:
            print(f"Unable to get simulation stats for lab {lab} . Exception Message {e}")

# update nodes struct with node details
def update_nodes_dict(url, auth_token):
    headers = get_headers(auth_token)
    try:
        node_data = requests.get(
            f"{url}{CML_API_VERSION}/nodes/", 
            headers=headers, verify=False).json()
        for item in node_data:
            node_id=item['id']
            nodes[node_id]=item
    except requests.RequestException as e:
        print(f"Unable to Get Node Data. Exception Message {e}")


def update_labs_dict(url, auth_token):
    headers = get_headers(auth_token)
    try:
        lab_data = requests.get(
            f"{url}{CML_API_VERSION}/labs?show_all=true", 
            headers=headers, verify=False).json()
        
        for lab_id in lab_data:
            labs[lab_id] = requests.get(
                f"{url}{CML_API_VERSION}/labs/{lab_id}", 
                headers=headers, verify=False).json()

            labs[lab_id]['lab_nodes'] = requests.get(
                f"{url}{CML_API_VERSION}/labs/{lab_id}/nodes", 
                headers=headers, verify=False).json()

            labs[lab_id]['lab_links'] = requests.get(
                f"{url}{CML_API_VERSION}/labs/{lab_id}/links",
                headers=headers, verify=False).json()     

    except requests.RequestException as e:
        print(f"Unable to Get Lab Data. Exception Msg: {e}")    

def update_system_dict(url, auth_token):
    headers = get_headers(auth_token)
    try:
        license = requests.get ( 
            f"{url}{CML_API_VERSION}/diagnostics/licensing",
            headers=headers, verify=False).json()
        system['licensing']=license
    except requests.RequestException as e:
        print("Unable to get Licensing Data. Eception Msg: {e}")

def update_system_health(url, auth_token):
    headers=get_headers(auth_token)
    try:
        sys_health=requests.get (
            f"{url}{CML_API_VERSION}/system_stats",
            headers=headers, verify=False).json()
        system['stats']=sys_health
    except requests.RequestException as e:
        print("Unable to get Sys Stats. Eception Msg: {e}")

# export data to json files.
def export_data_to_file():
    try:
        with open('nodes.json', 'w', encoding='utf-8') as f:
            json.dump(nodes, f, ensure_ascii=False, indent=4)
        with open('labs.json', 'w',encoding='utf-8') as f:
            json.dump(labs, f,ensure_ascii=False, indent=4)
        with open('system.json', 'w',encoding='utf-8') as f:
            json.dump(system, f,ensure_ascii=False, indent=4)            
    except Exception as e:
        print(f"Failed to export JSON data to files. Exception: {e}")


# main function to execute program
def main(server,username,password,export,actions):
    url=f"https://{server}/api"

    auth_token = get_token(url, username, password)

    # print summaries and details
    if 'health' in actions or 'all' in actions:
        update_system_dict(url,auth_token)
        update_system_health(url,auth_token)
        print_sys_health()
    if 'labs' in actions or 'all' in actions:
        update_labs_dict(url, auth_token)
        update_nodes_dict(url, auth_token)
        update_nodes_resource_util(url,auth_token)
        print_labs_summary(url)
        print_detailed_lab_info()

    if export:
        export_data_to_file()


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