from parsers.satellite_parser import SatelliteParser
from parsers.rinex_parser import RinexParser

from config import *

import zipfile
from pathlib import Path
import numpy as np

import requests
import os
import shutil
import gzip
import json

            
def upload_nav_file(year: int, yday: str, nav_filename: str, cookies: dict):
    logger.info(f"Uploading navigation file. Params: doy = {yday}, year={year}, filename={nav_filename}")
    
    href = f"https://simurg.space/files2/{year}/{yday}/nav/{nav_filename}"
    download_folder = f"{FILE_BASE_PATH}downloaded_files\\{year}\\{yday}"
    os.makedirs(download_folder, exist_ok=True)
    save_path = os.path.join(download_folder, nav_filename)
    
    logger.debug(f"Downloading nav file from {href} to {save_path}")
    download_nav_file(href, save_path)
    
    logger.debug(f"Unzipping file: {save_path}")
    extract_path = unzip_gz(save_path, download_folder)
    
    logger.info(f"Sending file to server. Path: {extract_path}")
    send_file(
        path=extract_path,
        cookies=cookies,
        url=UPLOAD_NAV_URL
    )
    return extract_path
    
    
def download_nav_file(url, save_path):
    logger.info(f"Downloading navigation file from {url}")
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info("Navigation file downloaded successfully")
        return save_path
    else:
        logger.error(f"Failed to download navigation file. Status code: {response.status_code}")
        response.raise_for_status()
        

def find_holes(file: SatelliteParser, data_period: int, timestep: int):
    data = file.get_data()
    logging_id = f'{file.get_filename()}'
    headers = file.get_headers()
    logger.debug(f"Retrieved data and headers. Headers: {headers} in {logging_id}")

    period_records = int((data_period * 60) / timestep)
    records_count = int(24*(60/data_period))
    logger.debug(f"Calculated period_records: {period_records}, records_count: {records_count} in {logging_id}")


    holes = {
        "actual": {},
        "potencial": {}
    }
    
    signals = headers[4:]
    logger.debug(f"Identified signals: {signals} in {logging_id}")
    
    if data is None:
        logger.warning(f"No data available in {logging_id}, initializing holes with -1")
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
        logger.warning(f"Adjusted signals due to unworking signals. New signals: {signals} in {logging_id}")

    
    records = 0
    was_data=False
    is_send_period_started = False
    prev_tsn = 0
    period_start_tsn = 0

    def check_for_hole():
        nonlocal datas, holes, records, curr_tsn, prev_tsn, is_send_period_started, was_data, period_start_tsn
        
        if np.all(datas == 0) and not is_send_period_started:
            if prev_tsn + 1 < curr_tsn:
                records += int(curr_tsn) - int(prev_tsn)-1
            prev_tsn = curr_tsn
            return

        if np.any(datas > 0) and not is_send_period_started:
            logger.debug(f"Sending period is started. Period without data: start_tsn = {period_start_tsn}, end_tsn = {curr_tsn-1} in {logging_id}")
            period_start_tsn = curr_tsn
            is_send_period_started = True
            if prev_tsn + 1 < curr_tsn:
                records += int(curr_tsn) - int(prev_tsn)-1
            prev_tsn = curr_tsn
            for signal in signals:
                holes["actual"][signal][-1] += 1 
                           
        if np.any(datas>0) and not was_data:
            was_data = True

        if np.any(datas > 0) and prev_tsn + 1 < curr_tsn:
            logger.debug(f"Data gap found between {period_start_tsn} and {curr_tsn-1} TSNs in {logging_id}")
            period_start_tsn = curr_tsn
            for signal in signals:
                holes["actual"][signal] += holes["potencial"][signal]
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
        
        if np.all(datas > 0):
            for signal in signals:
                if np.all(holes["potencial"][signal] == 0):
                    continue
                holes['actual'][signal]+=holes["potencial"][signal]
                holes["potencial"][signal] = np.zeros_like(holes["potencial"][signal])
            prev_tsn = curr_tsn
            return

        if np.all(datas == 0) and elev < ELEVATION:
            logger.debug(f"Data missing and elevation is low. Sending period end. Period with data: start_tsn = {period_start_tsn}, period_end = {curr_tsn-1} in {logging_id}")
            period_start_tsn = curr_tsn
            for signal in signals:
                if not was_data:
                    holes['actual'][signal][-1]=-1
                
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
        if records > period_records:
            end_number = 0 if is_send_period_started else -1
            
            for _ in range(records//period_records):
                for signal in signals:
                    holes["actual"][signal] = np.append(holes["actual"][signal], end_number)
                    holes["potencial"][signal] = np.append(holes["potencial"][signal], 0)
            was_data=False
            records = records%period_records
    
    if is_send_period_started:
        logger.debug(f"Last period was with data. start_tsn = {period_start_tsn}, end_tsn = {curr_tsn} in {logging_id}")
    else:
        logger.debug(f"Last period was without data. start_tsn = {period_start_tsn}, end_tsn = {curr_tsn} in {logging_id}")

    
                    
    for signal in signals:        
        holes["actual"][signal] += holes["potencial"][signal]           
                
    holes = holes["actual"]
    
    for signal in holes:
        missing_entries = records_count - len(holes[signal])
        if missing_entries > 0:
            logger.debug(f"Adding missing entries for signal: {signal}, count: {missing_entries} in {logging_id}")
            for _ in range(missing_entries):
                holes[signal] = np.append(holes[signal], -1)
    
    if unworking_signals_count > 0:
        logger.debug(f"Handling unworking signals, count: {unworking_signals_count} in {logging_id}")
        signals = headers[-unworking_signals_count:]
        for signal in signals:
            holes[signal] = np.full(records_count, -1)
    
    
    hole_count = 0
    for signal in signals:
        if np.any(holes[signal] > 0):
            positive_holes = holes[signal][holes[signal] > 0]
            hole_count += np.sum(positive_holes)
    
    logger.info(f"find_holes function completed successfully. Number of holes found: {hole_count} in {logging_id}")
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
    logger.info(f"Unzipping gz archive: {file_path}")
    with gzip.open(file_path, 'rb') as f_in:
        extract_path = os.path.join(extract_to_folder, os.path.basename(file_path)[:-3])
        with open(extract_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    logger.info(f"Gz archive unzipped to {extract_path}")
    return extract_path

def unzip_zip(
    file_path: Path,
    extract_to_folder: Path
):
    logger.info(f"Unzipping zip archive: {file_path}")
    
    files = []
    with zipfile.ZipFile(file_path, 'r') as z:
        file_names = z.namelist()
        if len(file_names) == 0:
            logger.error(f"Archive {file_path} is empty")
            raise ValueError("Empty archive")
        else:
            for name in file_names:
                files.append(z.extract(name, extract_to_folder))
                
    logger.info(f"Zip archive unzipped to {files}")
    return files


def send_file(path, cookies, url):
    logger.info(f"Sending file {path} to {url}")
    with open(path, "rb") as f:
        files = {"rinex": f}
        response = requests.post(url, files=files, cookies=cookies)
        if response.status_code == 200:
            logger.info(f"File sent successfully to {url}")
        else:
            logger.error(f"Failed to send file. Status code: {response.status_code}")
            response.raise_for_status()
    
def get_graph_data(signals: dict, task_id: str):
    logger.info(f"Preparing graph data from signals for task: {task_id}")
    
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
        
    logger.debug(f"Graph data successfully prepared for task: {task_id}")
    return graph_data

def download_sattelite_files(parser: RinexParser, task_id: str):
    try:
        logger.info(f"Downloading satellite files for task {task_id}")
        
        date = parser.get_date()
        year = date.year
        yday = str(date.timetuple().tm_yday).zfill(3)
        
        save_path = os.path.join(f'{FILE_BASE_PATH}result_csv', f'{yday}_{year}.zip')

        if os.path.exists(save_path):
            logger.info(f"Task {task_id} already completed. File exists at {save_path}")
            redis_client.set(task_id, json.dumps({'status': 'completed', 'result': save_path}))
            return
        
        redis_client.set(task_id, json.dumps({'status': 'processing'}))

        nav_filename = f'BRDC00IGS_R_{year}{yday}0000_01D_MN.rnx.gz'
        rinex_to_csv_processing_id = f"{parser.get_filename()}-_-{nav_filename}"
        cookies = {"rinex_to_csv_processing_id": rinex_to_csv_processing_id}

        logger.debug("Uploading navigation file")
        upload_nav_file(
            year=year,
            yday=yday,
            nav_filename=nav_filename,
            cookies=cookies
        )
        
        logger.debug("Uploading RINEX file")
        rinex_path = parser.get_filepath()
        send_file(
            path=rinex_path,
            cookies=cookies,
            url=UPLOAD_RINEX_URL
        )

        systems = parser.get_systems()
        timestep = parser.get_timestep()
        systems['timestep'] = int(timestep)      

        
        logger.debug("Posting signals data")
        response = requests.post(RUN_URL, json=systems, cookies=cookies)
        
        
        logger.debug("Retrieving result from server")
        response = requests.get(RESULT_URL, cookies=cookies)
        os.makedirs(f'{FILE_BASE_PATH}result_csv', exist_ok=True)
        
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info("Result file downloaded successfully")
        else:
            logger.error(f"Failed to retrieve result. Status code: {response.status_code}")
            response.raise_for_status()

        redis_client.set(task_id, json.dumps({'status': 'completed', 'result': save_path}))
    except Exception as e:
        logger.error(f"Error during file download process: {e}")
        redis_client.set(task_id, json.dumps({'status': 'failed', 'error': str(e)}))