# Kubernetes Flow Visibility (with Cisco Nexus Dashboard Insights)

## Overview

This tool is a standalone tool spun off from the multi-cloud visualization component of the Multicloud Middleware System (MMS). For network engineers providing network environments for Kubernetes systems in On-prem environments, they often do not understand the details of network communication inside Kubernetes systems, but are required to take on the huge responsibility of cloud-native applications not affecting customer experience due to communication failures in the underlying network. Many network management tools, such as Cisco Nexus Dashboard Insights, provide hardware-based, full-time, per-flow InBand Telemetry capabilities that can provide extensive data for analyzing abnormal traffic, but cannot be pinpointed to traffic related to cloud-native services for network engineers; and many cloud-native management tools, such as Cisco Service Mesh Manager (Calisti), have a lot of data on health information between cloud-native services, but nothing on the underlying network traffic. This tool can combine data from these existing tools to achieve clear anomalies locations and visibility of cloud-native data flows in the underlying network based on the source and destination of the user-selected cloud-native system, allowing network engineers to stop treating communications within the Kubernetes system as a black box and to provide proactive operations and maintenance of the cloud-native network environment to improve the customer experience of cloud-native services.

## Prerequisite

* Need to use CNI in tunnel-free mode in order to allow users on-prem underlying network to have visibility into the communication between services

* Currently this tool can be used with the Cisco Nexus Dashboard Insights (support for other traffic visualization tools will be provided in the future)

* Currently the data on the microservice topology and health status are collected statically. In the future, it will support dynamic extraction from tools such as Calisti

## Usage

* **'From' and 'To'**: The source and destination of a flow. Select different type will affect the display of subsequent content.

 - **Internal service:** the service which has the type of Cluster IP

 - **External:** the subnet/addresses outside the cluster

 - **NodePort service:** the service which has the type of NodePort

 - **Load Balancer:** the load balancer address when use the service which has the type of LoadBalancer

* **Record Time:** the time of the data record (Currently only support 'Live')

* **Namespace:** the namespace of the source or destination services

* **Service:** the Kubernetes service name

 - **♥ symbol:** the health score expressed as a percentage

 - **√ symbol:** a communication relationship with the source service is detected

* **Pod (IP address):** the pod name @ node name (pod IP address). If you want to input IP address manually (not recommended), you need to keep at least one pair of brackets

* **Dest port:** the destination pod's service port

* **Copy:** Based on your input, this tool will generate a set of flow filtering expressions, which in the current version can be used directly as input to NDI's flow analysis window (copied to clipboard). More tools will be supported in the future, such as StealthWatch.
