"""Download only the relevant nested NASA archive, then retain selected cells."""
import io
from pathlib import Path
from zipfile import ZipFile
from remotezip import RemoteZip

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://phm-datasets.s3.amazonaws.com/NASA/5.%20Battery%20Data%20Set.zip'

if __name__ == '__main__':
    dest = ROOT/'data/raw'
    dest.mkdir(parents=True, exist_ok=True)
    with RemoteZip(URL) as outer:
        raw = outer.read('5. Battery Data Set/1. BatteryAgingARC-FY08Q4.zip')
    with ZipFile(io.BytesIO(raw)) as inner:
        for name in ['B0005.mat', 'B0006.mat', 'B0007.mat', 'B0018.mat', 'README.txt']:
            (dest/name).write_bytes(inner.read(name))
    print('Downloaded four NASA cells. Run scripts/train.py next.')
