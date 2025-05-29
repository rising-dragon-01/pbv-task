def validate_vm(df):
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.compute import ComputeManagementClient
    from azure.mgmt.network import NetworkManagementClient
    import pandas as pd

    credential = DefaultAzureCredential()
    results = []

    fields_to_compare = [
        'IP Address', 'Subscription', 'Resource Group Name', 'Location', 'VM OS Time Zone', 'Size',
        'Operating System Type', 'Operating System', 'AD Domain', 'Admin Group', 'Availability Zone',
        'Availability Set', 'Availability Set Name', 'Fault Domain', 'Update Domain', 'ASR',
        'Secondary Region', 'Secondary Region Resource Group', 'OSDisk Category', 'OSDisk Resource Name',
        'OSDisk Size', 'DataDisk-1 Category', 'Datadisk-1 Resource Name', 'Mount Point',
        'DataDisk-1 Size', 'DataDisk-1 Caching', 'Shared disk', 'Max Shares', 'Storage Redundant',
        'AHUB', 'Reserved Instance', 'Backup Policy', 'SQL Database', 'SQL Edition/version',
        'SQL Collation', 'SQL Backup Policy', 'Update Group [Patch Window]', 'Virtual Network Name',
        'Subnet Name', 'ASG', 'Tags [ Role ]', 'Tags [ Patching Schedule ]', 'Tags [ ASR Enabled ]',
        'Tags [ BackupPolicy ]', 'Tags [ Billing ]', 'Tags [ Businesshours ]', 'Tags [ CreationDate ]',
        'Tags [ Internet Access ]', 'Tags [ LBName ]', 'Tags [ MPGTicketRef ]'
    ]
    ignore_values = ['NA', 'No', '']

    for _, row in df.iterrows():
        vm_name = row.get('ResourceName') or row.get('VM Name') or row.get('vm_name')
        resource_group = row.get('Resource Group Name') or row.get('resource_group')
        subscription_id = row.get('Subscription')
        if pd.isna(vm_name) or pd.isna(resource_group) or pd.isna(subscription_id):
            continue
        try:
            compute_client = ComputeManagementClient(credential, subscription_id)
            network_client = NetworkManagementClient(credential, subscription_id)
            vm = compute_client.virtual_machines.get(resource_group, vm_name, expand='instanceView')
            mismatch_details = []

            # Network info
            nic_ref = vm.network_profile.network_interfaces[0].id
            nic_name = nic_ref.split('/')[-1]
            nic = network_client.network_interfaces.get(resource_group, nic_name)
            ip_config = nic.ip_configurations[0]

            # Disks
            os_disk = compute_client.disks.get(resource_group, vm.storage_profile.os_disk.name)
            data_disks = vm.storage_profile.data_disks
            data_disk = data_disks[0] if data_disks else None

            # Tags
            tags = vm.tags or {}

            # Map Azure values for comparison
            azure_values = {
                'IP Address': ip_config.private_ip_address,
                'Subscription': subscription_id,
                'Resource Group Name': resource_group,
                'Location': vm.location.lower(),
                'VM OS Time Zone': '',  # Not directly available
                'Size': vm.hardware_profile.vm_size.lower(),
                'Operating System Type': str(vm.storage_profile.os_disk.os_type),
                'Operating System': vm.storage_profile.image_reference.offer if vm.storage_profile.image_reference else '',
                'AD Domain': '',
                'Admin Group': '',
                'Availability Zone': vm.zones[0] if vm.zones else '',
                'Availability Set': 'Yes' if vm.availability_set else 'No',
                'Availability Set Name': vm.availability_set.id.split('/')[-1] if vm.availability_set else '',
                'Fault Domain': str(vm.instance_view.platform_fault_domain) if vm.instance_view else '',
                'Update Domain': str(vm.instance_view.platform_update_domain) if vm.instance_view else '',
                'ASR': '',
                'Secondary Region': '',
                'Secondary Region Resource Group': '',
                'OSDisk Category': os_disk.sku.name if os_disk.sku else '',
                'OSDisk Resource Name': vm.storage_profile.os_disk.name,
                'OSDisk Size': str(os_disk.disk_size_gb),
                'DataDisk-1 Category': data_disk.sku.name if data_disk and data_disk.sku else '',
                'Datadisk-1 Resource Name': data_disk.name if data_disk else '',
                'Mount Point': '',
                'DataDisk-1 Size': str(data_disk.disk_size_gb) if data_disk else '',
                'DataDisk-1 Caching': data_disk.caching if data_disk else '',
                'Shared disk': 'Yes' if data_disk and getattr(data_disk, 'max_shares', 0) > 1 else 'No',
                'Max Shares': str(getattr(data_disk, 'max_shares', '')) if data_disk else '',
                'Storage Redundant': os_disk.sku.name if os_disk.sku else '',
                'AHUB': 'Yes' if getattr(vm, 'license_type', None) else 'No',
                'Reserved Instance': '',
                'Backup Policy': '',
                'SQL Database': '',
                'SQL Edition/version': '',
                'SQL Collation': '',
                'SQL Backup Policy': '',
                'Update Group [Patch Window]': '',
                'Virtual Network Name': ip_config.subnet.id.split('/')[-3] if ip_config.subnet else '',
                'Subnet Name': ip_config.subnet.id.split('/')[-1] if ip_config.subnet else '',
                'ASG': ip_config.application_security_groups[0].id.split('/')[-1] if ip_config.application_security_groups else '',
                'Tags [ Role ]': tags.get('Role', ''),
                'Tags [ Patching Schedule ]': tags.get('Patching Schedule', ''),
                'Tags [ ASR Enabled ]': tags.get('ASR Enabled', ''),
                'Tags [ BackupPolicy ]': tags.get('BackupPolicy', ''),
                'Tags [ Billing ]': tags.get('Billing', ''),
                'Tags [ Businesshours ]': tags.get('Businesshours', ''),
                'Tags [ CreationDate ]': tags.get('CreationDate', ''),
                'Tags [ Internet Access ]': tags.get('Internet Access', ''),
                'Tags [ LBName ]': tags.get('LBName', ''),
                'Tags [ MPGTicketRef ]': tags.get('MPGTicketRef', '')
            }

            for field in fields_to_compare:
                excel_value = str(row.get(field, '')).strip()
                if excel_value in ignore_values:
                    continue
                azure_value = str(azure_values.get(field, '')).strip()
                if excel_value.lower() != azure_value.lower():
                    mismatch_details.append(f"{field}: Excel={excel_value}, Azure={azure_value}")

            status = 'Pass' if not mismatch_details else 'Fail'
            results.append({
                "Resource Name": vm_name,
                "Status": status,
                "Mismatched Fields": '; '.join(mismatch_details) if mismatch_details else ''
            })

        except Exception as e:
            results.append({
                "Resource Name": vm_name,
                "Status": "Fail",
                "Mismatched Fields": f"Error accessing VM: {str(e)}"
            })

    return results
