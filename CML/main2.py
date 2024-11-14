import requests 
import json
import pprint
import urllib3
from rich.table import Table
from rich.text import Text
from rich.console import Console

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# labs will be a dict that will be populated with lab topology data, including nodes, links and other related data.
labs={}
nodes={}

def get_token(url, username, password):
    api = "/v0/authenticate"
    url += api

#    headers = {
#		'Content-Type': 'application/json',
#		'accept': 'application/json'
#	}

    payload = {
		"username": username,
		"password": password
	}

    try:
        token = requests.post(url, json=payload, verify=False).json()
    except Exception as e:
        printf(f"Unable to Get Token. Exception Msg {e}")

    return token


def print_labs_summary(url):
    print("#" + " " + "Simulated labs on CML" + ": " + str(len(labs)))

    table = Table(title=f"Labs on {url}", title_style='bold')
    table.add_column('LabID', justify='left', style='cyan')
    table.add_column('State', justify='left', style='cyan')
    table.add_column('Lab Title', justify='left', style='cyan')
    table.add_column('Owner', justify='left', style='cyan')
    table.add_column('# Nodes', justify='left', style='cyan')
    table.add_column('# Links', justify='left', style='cyan')

    for labid in labs.keys():
            table.add_row(
                labid, 
                Text(labs[labid]['state'], style='green' if labs[labid]['state']=='STARTED' else 'cyan'),
                labs[labid]['lab_title'],
                labs[labid]['owner_username'],
                str(labs[labid]['node_count']),
                str(labs[labid]['link_count'])
            )
    console = Console()
    console.print()
    console.print(table)



def print_detailed_lab_info():

    for labid in labs.keys():
        table = Table(title=f"Lab Detailed Info\n LabID: {labid}\n LabTitle: {labs[labid]['lab_title']}", title_style='bold')
        table.add_column('NodeID', justify='left', style='cyan')
        table.add_column('Label', justify='left', style='cyan')
        table.add_column('Node Definition', justify='left', style='cyan')
        table.add_column('State', justify='left', style='cyan')
        table.add_column('CPU REQ', justify='left', style='cyan')
        table.add_column('RAM REQ', justify='left', style='cyan')
        table.add_column('CPU use', justify='left', style='cyan')
        table.add_column('RAM use', justify='left', style='cyan')

        for lab_node in labs[labid]['lab_nodes']:

            if 'util' in nodes[lab_node] and 'cpu_usage' in nodes[lab_node]['util'] and 'ram_usage' in nodes[lab_node]['util']:
                cpu_used=nodes[lab_node]['util']['cpu_usage']
                mem_used=nodes[lab_node]['util']['ram_usage']
            else:
                mem_used=cpu_used=0.0

            table.add_row(
                lab_node,
                nodes[lab_node]['label'],
                nodes[lab_node]['node_definition'],
                Text(nodes[lab_node]['state'], style='green' if nodes[lab_node]['state']=='BOOTED' else 'cyan'),
                str(nodes[lab_node]['cpus']),
                str(nodes[lab_node]['ram']),
                str(cpu_used),
                str(mem_used)
            )
        console = Console()
        console.print()
        console.print(table)


def update_nodes_resource_util(url,auth_token):
    headers = {
		'Content-Type': 'application/json',
		'accept': 'application/json',
        'authorization': f"Bearer {auth_token}"
	}

    for lab in labs.keys():
        try:
            sim_data = requests.get(url + f"/v0/labs/" + lab + f"/simulation_stats", headers=headers, verify=False).json()
           # pprint.pprint(sim_data)
            for node_key, node_details in sim_data['nodes'].items():
                nodes[node_key]['util']=node_details
        except Exception as e:
            print(f"Unable to Get Node Data. Exception Message {e}")


def update_nodes_dict(url, auth_token):
    headers = {
		'Content-Type': 'application/json',
		'accept': 'application/json',
        'authorization': f"Bearer {auth_token}"
	}
    try:
        node_data = requests.get(url + f"/v0/nodes/", headers=headers, verify=False).json()
        for dic in node_data:
            node_id=dic['id']
            nodes[node_id]=dic
    except Exception as e:
        print(f"Unable to Get Node Data. Exception Message {e}")


def update_labs_dict(url, auth_token):
    headers = {
		'Content-Type': 'application/json',
		'accept': 'application/json',
        'authorization': f"Bearer {auth_token}"
	}
    try:
        lab_data = requests.get(url + f"/v0/labs" + f"?show_all=true", headers=headers, verify=False).json()
        
        for lab_id in lab_data:

            labs[lab_id]={}
            lab_data_detailed = requests.get(url + f"/v0/labs/" + lab_id, headers=headers, verify=False).json()
            labs[lab_id]=lab_data_detailed

            lab_nodes = requests.get(url + f"/v0/labs/" + lab_id + f"/nodes", headers=headers, verify=False).json()
            labs[lab_id]['lab_nodes']=lab_nodes             

            lab_links = requests.get(url + f"/v0/labs/" + lab_id + f"/links", headers=headers, verify=False).json()
            labs[lab_id]['lab_links']=lab_links        

    except Exception as e:
        print(f"Unable to Get Lab Data. Exception Msg {e}")    


def main(server,username,password):
    url=f"https://{server}/api"

    auth_token = get_token(url, username, password)

    update_labs_dict(url, auth_token)
    update_nodes_dict(url, auth_token)
    update_nodes_resource_util(url,auth_token)

    with open('nodes.json', 'w', encoding='utf-8') as f:
        json.dump(nodes, f, ensure_ascii=False, indent=4)
    with open('labs.json', 'w',encoding='utf-8') as f:
        json.dump(labs, f,ensure_ascii=False, indent=4)

    print_labs_summary(url)
    print_detailed_lab_info()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description = "Report on Lab")
    parser.add_argument('--server', dest = 'server',
                        help = 'CML Server IP',
                        required = True,
                        default = None)   
    parser.add_argument('--username', dest = 'username',
                        help = 'CML Username',
                        required = True,
                        default = None)
    parser.add_argument('--password', dest = 'password',
                        help = 'CML Password',
                        required = True,
                        default = None)

    args = parser.parse_args()

    main(args.server, args.username, args.password)