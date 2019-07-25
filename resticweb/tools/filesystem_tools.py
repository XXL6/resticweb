import os

def get_system_drives():
    import psutil
    drive_array = psutil.disk_partitions(True)
    return_drive_list = []
    for item in drive_array:
        return_drive_list.append({
            'device': item.device,
            'mountpoint': item.mountpoint,
            'fstype': item.fstype,
            'opts': item.opts })
    return return_drive_list

def get_directory_contents(path):
    file_array = os.scandir(path)
    return_file_list = []
    for file in file_array:
        return_file_list.append({
            'name': file.name,
            'is_file': file.is_file(),
            'is_dir': file.is_dir(),
            'path': file.path})
    return return_file_list

