#!/usr/bin/env python
###################################################################################
#                           Written by Wei, Hang                                  #
#                          weihanghank@gmail.com                                  #
###################################################################################
"""
Extract endpoints information about specific namespaces, services from Kubernetes cluster,
convert them into communication relations across nodes, output source and destination addresses
of these communication relations as well as port numbers, time ranges, etc. so that they can be
directly used to build flow table filter expressions for Nexus Dashboard Insights(NDI).
"""
import tkinter as tk
from tkinter import ttk, Tk
import tkinter.messagebox
from my_py.configbyssh import *
import json
import re

# HOST_INFO import from configbyssh module

# Load kubernetes status (from live system or a TSDB), no further extraction required for subsequent processing
TIME = ["1 minute ago", "15 minutes ago"]
try:
    NAMESPACES = [i.decode('utf-8') for i in configbyssh(HOST_INFO, "kubectl get ns | awk '{print $1}'").splitlines()]
    del NAMESPACES[0]
    NODES = [i.decode('utf-8') for i in
             configbyssh(HOST_INFO, "kubectl get nodes -o wide | awk '{print $1,$6}'").splitlines()]
    del NODES[0]
    SERVICES = [i.decode('utf-8') for i in configbyssh(HOST_INFO, "kubectl get svc -A").splitlines()]
    del SERVICES[0]
    ENDPOINTS = json.loads(configbyssh(HOST_INFO, "kubectl get endpointslices -A -ojson"))
except:
    tk.messagebox.showerror(title="Initialization Failure",
                            message="Check if you can connect to your kubernetes system.")
    exit(1)  # TODO: Load local test data instead of live system

# TODO: get service relationship and service health score (e.g. from Calisti)
SVC_RELATION = {
    "smm-demo": {
        "analytics": ["bookings"],
        "bookings": ["analytics", "payments"],
        "catalog": ["movies", "frontpage"],
        "database": ["movies"],
        "frontpage": ["catalog"],
        "movies": ["catalog", "mysql", "database"],
        "mysql": ["movies"],
        "notifications": ["payments"],
        "payments": ["notifications"],
        "postgresql": ["frontpage"]
    },
    "test02": {
        "blogsvc": ["dbsvc"],
        "dbsvc": ["blogsvc"]
    }
}
SVC_HEALTH = {
    "smm-demo": {
        "analytics": "100",
        "bookings": "100",
        "catalog": "100",
        "database": "100",
        "frontpage": "100",
        "movies": "100",
        "mysql": "100",
        "notifications": "100",
        "payments": "100",
        "postgresql": "100"
    },
    "test02": {
        "blogsvc": "100",
        "dbsvc": "100"
    }
}


def get_svc_list(ns, type):
    """
    This function returns service list based on specific namespace
    """
    svc_list = []

    for svc_line in SERVICES:
        svc_line_list = svc_line.split()
        if ns == svc_line_list[0]:
            if type == "NodePort service" and svc_line_list[2] == "NodePort" or type == "Internal service":
                svc_list.append(svc_line_list[1])

    return svc_list  # Note that list maybe empty


def get_ep_list(ns, svc):
    """
    This function returns endpoints list based on specific namespace and service
    """
    ep_list = []
    dport_list = []
    for slice in ENDPOINTS["items"]:
        # make sure we select the slice with correct corresponding namespace and svc, if there not, return empty list
        if slice["metadata"]["namespace"] == ns and slice["metadata"].get("ownerReferences"):
            if slice["metadata"]["ownerReferences"][0]["name"] == svc:
                for ep in slice["endpoints"]:  # extract ep's address, nodeName and name information
                    ep_list.append(
                        {"address": ep["addresses"][0], "nodeName": ep["nodeName"], "name": ep["targetRef"]["name"]})
                for port in slice["ports"]:  # extract corresponding port and protocol information
                    dport_list.append({"port": str(port["port"]), "protocol": port["protocol"]})
                break

    # return endpoint list and destination port list at the same time
    return ep_list, dport_list


def main():
    """
    Push the commands and get the response
    """

    def copyto(str):
        """
        This function copy the flow filter string to clipboard for you to filter flow in NDI
        """
        cp = Tk()
        cp.withdraw()
        cp.clipboard_clear()
        cp.clipboard_append(str)
        cp.update()

    def get_ip(str):
        """
        This function is to extract ip address from a string
        """
        ip = ""

        if 0 < str.find(" (") < str.find(")"):
            ip = str[str.find(" (") + 2:-1]
        elif str[str.find(" ") + 1:]:
            ip = str[str.find(" ") + 1:]
        else:
            ip = str

        if re.match("\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", ip) is not None:
            return ip
        else:
            return ""

    def get_port(str):
        """
        This function is to extract port and protocol from a string
        """
        port = ""
        protocol = ""

        if 0 < str.find(" (") < str.find(")"):
            port = str[:str.find(" (")]
            protocol = str[str.find(" (") + 2: -1]
        elif 0 < str.find(":") < str.find("/"):
            port = str[str.find(":") + 1: str.find("/")]
            protocol = str[str.find("/") + 1:]

        return port, protocol

    def do_copy():
        """
        This function triggers the copy behaviour
        """
        pod1 = get_ip(cbl_pod1.get())
        pod2 = get_ip(cbl_pod2.get())
        port, protocol = get_port(cbl_port.get())

        # TODO: record time condition: time = ...

        copystr = ""
        # extract IP address and dst port from the actual combobox list, user can input those info manually with '(...)'
        if pod1:
            copystr += '"Source Address" == "{}"; '.format(pod1)
        if pod2:
            copystr += '"Destination Address" == "{}"; '.format(pod2)
        if port and protocol:
            copystr += '"Destination Port" == "{}"; '.format(port)
            copystr += '"Protocol" == "{}"; '.format(protocol)

        # output to terminal
        print("You can manually copy following string to Nexus Dashboard Flow Browser:\n", copystr)
        copyto(copystr)
        tk.messagebox.showinfo('Congratulations!', "The flow filter string was successfully copied to clipboard!")

    def do_cancel():
        """
        doing cancel
        """
        exit(0)

    def set_svc_list1(event):
        """
        This function is to set svc list of source
        """
        ns = cbl_ns1.get()
        svc_list = get_svc_list(ns, cbl_fr.get())
        new_svc_list = []

        for svc_name in svc_list:
            health_mark = "♥ ---%     "
            if SVC_HEALTH.get(ns):
                if SVC_HEALTH[ns].get(svc_name):  # to see if there is corresponding ns and svc in health database
                    health_mark = "♥ " + "%03d" % int(SVC_HEALTH[ns][svc_name]) + "%     "
            new_svc_list.append(health_mark + svc_name)

        cbl_svc1["values"] = ["                  ------  Please select a service  ------"] + new_svc_list
        cbl_svc1.current(0)
        cbl_pod1["values"] = ["                    ------  Please select a pod  ------"]
        cbl_pod1.current(0)

    def set_svc_list2(event):
        """
        This function is to set svc list of destination
        """
        ns = cbl_ns2.get()
        svc_list = get_svc_list(ns, cbl_to.get())
        new_svc_list = []

        for svc_name in svc_list:
            health_mark = "♥ ---%"
            relation_mark = " --  "
            if SVC_HEALTH.get(ns):
                if SVC_HEALTH[ns].get(svc_name):
                    health_mark = "♥ " + "%03d" % int(SVC_HEALTH[ns][svc_name]) + "%"
            if SVC_RELATION.get(cbl_ns1.get()):  # mark relationship based on source svc
                if SVC_RELATION[cbl_ns1.get()].get(cbl_svc1.get()[11:]):  # if source svc exists in relation database
                    if svc_name in SVC_RELATION[cbl_ns1.get()][cbl_svc1.get()[11:]]:  # AND it's related to dst svc
                        relation_mark = " √   "

            new_svc_list.append(health_mark + relation_mark + svc_name)

        cbl_svc2["values"] = ["                  ------  Please select a service  ------"] + new_svc_list
        cbl_svc2.current(0)
        if cbl_to.get() == "Internal service":
            cbl_pod2["values"] = ["                    ------  Please select a pod  ------"]  # reset last selection
            cbl_pod2.current(0)

        cbl_port["values"] = ["                 ------  Please select a dest port  ------"]  # reset last selection
        cbl_port.current(0)

    def set_pod_list1(event):
        """
        This function is to set pod list 1
        """
        ep_list, port_list = get_ep_list(cbl_ns1.get(), cbl_svc1.get()[11:])
        pod_list = []
        for ep in ep_list:
            pod_list.append(ep["name"] + " @ " + ep["nodeName"] + " (" + ep["address"] + ")")
        if pod_list:  # if pod list is not empty
            cbl_pod1["values"] = pod_list  # TODO: program pod list to reflect pod health score
            cbl_pod1.current(0)

    def svc2_bind(event):
        """
        This function is the action binding to svc2
        """
        if cbl_to.get() == "Internal service":
            set_pod_list2()
        elif cbl_to.get() == "NodePort service":
            set_nodeport(cbl_ns2.get(), cbl_svc2.get()[11:])

    def set_nodeport(ns, svc):
        """
        This function is to set the nodeport
        """
        for svc_line in SERVICES:
            svc_line_list = svc_line.split()
            if ns == svc_line_list[0] and svc == svc_line_list[1]:
                cbl_port["values"] = svc_line_list[5].split()

    def set_pod_list2():
        """
        This function is to set pod list 2
        """
        ep_list, port_list = get_ep_list(cbl_ns2.get(), cbl_svc2.get()[11:])

        pod_list = []
        for ep in ep_list:
            pod_list.append(ep["name"] + " @ " + ep["nodeName"] + " (" + ep["address"] + ")")
        if pod_list:
            cbl_pod2["values"] = pod_list  # TODO: program pod list to reflect health score
            cbl_pod2.current(0)

        # set destination pod's port
        dstport_list = []
        for port in port_list:
            dstport_list.append(port["port"] + " (" + port["protocol"] + ")")
        cbl_port["values"] = ["                 ------  Please select a dest port  ------"] + dstport_list

    def set_ui_fr(event):
        """
        This function is to set dynamic ui on the left
        """
        label = cbl_fr.get()
        if label == "Internal service":
            lb_ns1.config(state='normal')
            lb_svc1.config(state='normal')
            lb_pod1.config(text="Pod (IP address):")
            cbl_ns1.config(state='normal')
            cbl_svc1.config(state='normal')
            cbl_pod1["values"] = ["                    ------  Please select a pod  ------"]
        elif label == "External":
            lb_ns1.config(state='disabled')
            lb_svc1.config(state='disabled')
            lb_pod1.config(text="External IP:")
            cbl_ns1.config(state='disabled')
            cbl_svc1.config(state='disabled')
            cbl_pod1["values"] = ["               ------  Please input an IP address  ------"]

        cbl_pod1.current(0)
        cbl_ns1["values"] = ["                  ------  Please select a namespace  ------"] + NAMESPACES
        cbl_ns1.current(0)
        cbl_svc1["values"] = ["                  ------  Please select a service  ------"]
        cbl_svc1.current(0)

    def set_ui_to(event):
        """
        This function is to set dynamic ui on the right
        """
        label = cbl_to.get()
        if label == "Internal service":
            lb_ns2.config(state='normal')
            lb_svc2.config(state='normal')
            lb_pod2.config(text="Pod (IP address):")
            cbl_ns2.config(state='normal')
            cbl_svc2.config(state='normal')
            cbl_pod2["values"] = ["                    ------  Please select a pod  ------"]
        elif label == "External":
            lb_ns2.config(state='disabled')
            lb_svc2.config(state='disabled')
            lb_pod2.config(text="External IP:")
            cbl_ns2.config(state='disabled')
            cbl_svc2.config(state='disabled')
            cbl_pod2["values"] = ["               ------  Please input an IP address  ------"]
        elif label == "NodePort service":
            lb_ns2.config(state='normal')
            lb_svc2.config(state='normal')
            lb_pod2.config(text="Node IP:")
            cbl_ns2.config(state='normal')
            cbl_svc2.config(state='normal')
            cbl_pod2["values"] = ["                    ------  Please select a node  ------"] + NODES

        cbl_pod2.current(0)
        cbl_ns2["values"] = ["                  ------  Please select a namespace  ------"] + NAMESPACES
        cbl_ns2.current(0)
        cbl_svc2["values"] = ["                  ------  Please select a service  ------"]
        cbl_svc2.current(0)
        cbl_port["values"] = ["                 ------  Please select a dest port  ------"]
        cbl_port.current(0)

    # window is the obj name
    window = tk.Tk()
    window.title('Cloud-Native Flow Visibility v0.3 by Wei Hang')
    window.geometry('1120x390')

    # Labels on the left
    lb_fr = tk.Label(window, width=16, font=("Arial", 10), anchor='e', text="From:")
    lb_fr.place(x=0, y=50, anchor='nw')

    lb_time = tk.Label(window, width=16, font=("Arial", 10), anchor='e', text="Record Time:")
    lb_time.place(x=0, y=100, anchor='nw')

    lb_ns1 = tk.Label(window, width=16, font=("Arial", 10), anchor='e', text="Namespace:")
    lb_ns1.place(x=0, y=150, anchor='nw')

    lb_svc1 = tk.Label(window, width=16, font=("Arial", 10), anchor='e', text="Service:")
    lb_svc1.place(x=0, y=200, anchor='nw')

    lb_pod1 = tk.Label(window, width=16, font=("Arial", 10), anchor='e', text="Pod (IP address):")
    lb_pod1.place(x=0, y=250, anchor='nw')

    # Combo Box Lists on the left
    cbl_fr = ttk.Combobox(window, font=("Arial", 10), width=50)
    cbl_fr["values"] = ["Internal service", "External", "NodePort service (inbound 2nd/3rd hop)",
                        "Load Balancer (inbound 2nd/3rd hop)"]  # TODO
    cbl_fr.current(0)
    cbl_fr.bind("<<ComboboxSelected>>", set_ui_fr)
    cbl_fr.place(x=150, y=50, anchor='nw')

    cbl_time = ttk.Combobox(window, font=("Arial", 10), width=50)
    cbl_time["values"] = ["Live"] + TIME
    cbl_time.current(0)
    cbl_time.place(x=150, y=100, anchor='nw')

    cbl_ns1 = ttk.Combobox(window, font=("Arial", 10), width=50)
    cbl_ns1["values"] = ["                  ------  Please select a namespace  ------"] + NAMESPACES
    cbl_ns1.current(0)
    cbl_ns1.bind("<<ComboboxSelected>>", set_svc_list1)
    cbl_ns1.place(x=150, y=150, anchor='nw')

    cbl_svc1 = ttk.Combobox(window, font=("Arial", 10), width=50)
    cbl_svc1["values"] = ["                  ------  Please select a service  ------"]
    cbl_svc1.current(0)
    if cbl_fr.get() == "Internal service":
        cbl_svc1.bind("<<ComboboxSelected>>", set_pod_list1)
    cbl_svc1.place(x=150, y=200, anchor='nw')

    cbl_pod1 = ttk.Combobox(window, font=("Arial", 10), width=50)
    cbl_pod1["values"] = ["                    ------  Please select a pod  ------"]
    cbl_pod1.current(0)
    cbl_pod1.place(x=150, y=250, anchor='nw')

    # Lables on the right
    lb_to = tk.Label(window, width=16, font=("Arial", 10), anchor='e', text="To:")
    lb_to.place(x=550, y=50, anchor='nw')

    lb_ns2 = tk.Label(window, width=16, font=("Arial", 10), anchor='e', text="Namespace:")
    lb_ns2.place(x=550, y=100, anchor='nw')

    lb_svc2 = tk.Label(window, width=16, font=("Arial", 10), anchor='e', text="Service:")
    lb_svc2.place(x=550, y=150, anchor='nw')

    lb_pod2 = tk.Label(window, width=16, font=("Arial", 10), anchor='e', text="Pod (IP address):")
    lb_pod2.place(x=550, y=200, anchor='nw')

    lb_port = tk.Label(window, width=16, font=("Arial", 10), anchor='e', text="Dest port")
    lb_port.place(x=550, y=250, anchor='nw')

    # Combo Box Lists on the right
    cbl_to = ttk.Combobox(window, font=("Arial", 10), width=50)
    cbl_to["values"] = ["Internal service", "External", "NodePort service", "Load Balancer service"]  # TODO
    cbl_to.current(0)
    cbl_to.bind("<<ComboboxSelected>>", set_ui_to)
    cbl_to.place(x=700, y=50, anchor='nw')

    cbl_ns2 = ttk.Combobox(window, font=("Arial", 10), width=50)
    cbl_ns2["values"] = ["                  ------  Please select a namespace  ------"] + NAMESPACES
    cbl_ns2.current(0)
    cbl_ns2.bind("<<ComboboxSelected>>", set_svc_list2)
    cbl_ns2.place(x=700, y=100, anchor='nw')

    cbl_svc2 = ttk.Combobox(window, font=("Arial", 10), width=50)
    cbl_svc2["values"] = ["                  ------  Please select a service  ------"]
    cbl_svc2.current(0)
    cbl_svc2.bind("<<ComboboxSelected>>", svc2_bind)
    cbl_svc2.place(x=700, y=150, anchor='nw')

    cbl_pod2 = ttk.Combobox(window, font=("Arial", 10), width=50)
    cbl_pod2["values"] = ["                    ------  Please select a pod  ------"]
    cbl_pod2.current(0)
    cbl_pod2.place(x=700, y=200, anchor='nw')

    cbl_port = ttk.Combobox(window, font=("Arial", 10), width=50)
    cbl_port["values"] = ["                 ------  Please select a dest port  ------"]
    cbl_port.current(0)
    cbl_port.place(x=700, y=250, anchor='nw')

    # Buttons
    bt_copy = tk.Button(window, text='Copy', width=15, height=2, font=("Arial", 10), command=do_copy)
    bt_copy.place(x=400, y=315, anchor='nw')

    bt_cancel = tk.Button(window, text='Cancel', width=15, height=2, font=("Arial", 10), command=do_cancel)
    bt_cancel.place(x=620, y=315, anchor='nw')

    # Window's mainloop
    window.mainloop()


if __name__ == '__main__':
    main()
