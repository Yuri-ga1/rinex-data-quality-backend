from parsers.satellite_parser import SatelliteParser
from config import *

import zipfile
from pathlib import Path
import numpy as np

import requests
import os
import shutil
import gzip

            
def upload_nav_file(year: int, yday: str, nav_filename: str, cookies: dict):
    href = f"https://simurg.space/files2/{year}/{yday}/nav/{nav_filename}"
    
    download_folder = f"{FILE_BASE_PATH}downloaded_files\\{year}\\{yday}"
    os.makedirs(download_folder, exist_ok=True)
    save_path = os.path.join(download_folder, nav_filename)
    
    download_nav_file(href, save_path)
    extract_path = unzip_gz(save_path, download_folder)
    
    send_file(
        path=extract_path,
        cookies=cookies,
        url=UPLOAD_NAV_URL
    )
    return extract_path
    
    
def download_nav_file(url, save_path):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return save_path
    else:
        response.raise_for_status()
        

def find_holes(file: SatelliteParser, data_period: int, timestep: int):
    data = file.get_data()
    headers = file.get_headers()

    period_records = int((data_period * 60) / timestep)
    records_count = int(24*(60/data_period))

    holes = {
        "actual": {},
        "potencial": {}
    }
    
    signals = headers[4:]
    if data is None:
        holes = holes["actual"]
        for signal in signals:
            holes[signal] = np.full(records_count, -1)
        return holes
    
    for signal in signals:
        holes["actual"][signal] = np.array([-1]) 
        holes["potencial"][signal] = np.array([0]) 
    
    unworking_signals_count = 0 
    if len(signals) != len(data[1][4:]):
        unworking_signals_count = len(signals) - len(data[1][4:])
        signals = signals[:-unworking_signals_count]
    
    records = 0
    curr_potencial_holes=0
    is_send_period_started = False
    prev_tsn = 0

    def check_for_hole():
        nonlocal datas, holes, records, curr_tsn, prev_tsn, is_send_period_started, curr_potencial_holes
        
        if np.all(datas == 0) and not is_send_period_started:
            if prev_tsn + 1 < curr_tsn:
                records += int(curr_tsn) - int(prev_tsn)-1
            prev_tsn = curr_tsn
            return

        if np.any(datas > 0) and not is_send_period_started:
            is_send_period_started = True
            prev_tsn = curr_tsn
            for signal in signals:
                holes["actual"][signal][-1] += 1

        if np.any(datas > 0) and prev_tsn + 1 < curr_tsn:
            for signal in signals:
                holes["actual"][signal] = holes["actual"][signal] + holes["potencial"][signal]
                holes['actual'][signal][-1] += int(curr_tsn) - int(prev_tsn)
                
            records += int(curr_tsn) - int(prev_tsn)
            prev_tsn = curr_tsn
            return

        if np.any(datas > 0) and np.any(datas == 0):
            for value, signal in zip(datas, signals):
                if value == 0:
                    holes['actual'][signal][-1] += 1
            
                holes["actual"][signal] = holes["actual"][signal] + holes["potencial"][signal]
                holes["potencial"][signal] = np.zeros_like(holes["potencial"][signal])
            
            prev_tsn = curr_tsn
            return

        if np.all(datas == 0) and elev > ELEVATION:
            for signal in signals:
                holes['potencial'][signal][-1]+=1
            prev_tsn = curr_tsn
            return

        if np.all(datas == 0) and elev < ELEVATION:
            for signal in signals:
                holes["potencial"][signal] = np.zeros_like(holes["potencial"][signal])
            
            is_send_period_started = False
            prev_tsn = curr_tsn
            return

        prev_tsn = curr_tsn

    for row in data:
        curr_tsn = row[0]
        elev = row[2]
        datas = row[4:]
        
        records += 1
        check_for_hole()
        if records >= period_records:
            end_number = 0 if is_send_period_started else -1
            for _ in range(records//period_records):
                for signal in signals:
                    holes["actual"][signal] = np.append(holes["actual"][signal], end_number)
                    holes["potencial"][signal] = np.append(holes["potencial"][signal], 0)
            records = records%period_records
                
                
    holes = holes["actual"]
    for signal in holes:
        missing_entries = records_count - len(holes[signal])
        if missing_entries > 0:
            for _ in range(missing_entries):
                holes[signal] = np.append(holes[signal], 0)
    
    if unworking_signals_count > 0:
        signals = headers[-unworking_signals_count:]
        for signal in signals:
            holes[signal] = np.full(records_count, -1)
                
    return holes
 
 
def convert_numpy_to_list(d):
    if isinstance(d, dict):
        return {k: convert_numpy_to_list(v) for k, v in d.items()}
    elif isinstance(d, np.ndarray):
        return d.tolist()
    elif isinstance(d, list):
        return [convert_numpy_to_list(i) for i in d]
    else:
        return d

        
def unzip_gz(file_path, extract_to_folder):
    with gzip.open(file_path, 'rb') as f_in:
        extract_path = os.path.join(extract_to_folder, os.path.basename(file_path)[:-3])
        with open(extract_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    return extract_path

def unzip_zip(
    file_path: Path,
    extract_to_folder: Path
):
    files = []
    with zipfile.ZipFile(file_path, 'r') as z:
        file_names = z.namelist()
        if len(file_names) == 0:
            raise ValueError("Empty archive")
        else:
            for name in file_names:
                files.append(z.extract(name, extract_to_folder))
    return files


def send_file(path, cookies,  url):
    with open(path, "rb") as f:
        files = {"rinex": f}
        requests.post(url, files=files, cookies=cookies)
    
def get_graph_data(signals: dict):
    graph_data = []
    for signal in signals:
        s = {}
        s['id'] = signal[0].upper( )
        s["data"] = []
        for option in signals[signal]:
            s['data'].append({
                'x': option,
                'y': 'Complete'
            })
        graph_data.append(s)
    return graph_data