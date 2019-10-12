from .repository import ResticRepository
from resticweb.dateutil import parser

# this is a ResticRepository interface wrapper that formats the
# raw snapshot data to be more suitable for the internal database

class ResticRepositoryFormatted(ResticRepository):

    def __init__(self, address, password, global_credentials=None, resticweb_repo_id=None):
        super().__init__(address, password, global_credentials)
        self.resticweb_repo_id = resticweb_repo_id

    def get_snapshots(self, snapshot_id=None):
        snapshots = super().get_snapshots(snapshot_id=snapshot_id)
        if snapshots:
            for item in snapshots:
                item['snap_id'] = item.pop('id')
                item['snap_short_id'] = item.pop('short_id')
                item['snap_time'] = item.pop('time')
                if item['snap_time']:
                    main_time = item['snap_time'][:-7]
                    extra = item['snap_time'][-6:]
                    main_time = main_time + extra
                    # item['snap_time'] = datetime.strptime(main_time, "%Y-%m-%dT%H:%M:%S.%f%z")
                    item['snap_time'] = parser.parse(main_time)
        return snapshots

    def get_snapshot_ls(self, snapshot_id):
        snapshot_objects = super().get_snapshot_ls(snapshot_id)
        for snapshot_object in snapshot_objects:
            if snapshot_object.get('mtime'):
                try:
                    snapshot_object['mtime'] = parser.parse(snapshot_object['mtime'])
                except ValueError:
                    snapshot_object['mtime'] = None
                snapshot_object['modified_time'] = snapshot_object.pop("mtime")
            if snapshot_object.get('atime'):
                try:
                    snapshot_object['atime'] = parser.parse(snapshot_object['atime'])
                except ValueError:
                    snapshot_object['atime'] = None
                snapshot_object['accessed_time'] = snapshot_object.pop("atime")
            if snapshot_object.get('ctime'):
                try:
                    snapshot_object['ctime'] = parser.parse(snapshot_object['ctime'])
                except ValueError:
                    snapshot_object['ctime'] = None
                snapshot_object['created_time'] = snapshot_object.pop("ctime")
        return snapshot_objects