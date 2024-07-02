from fastapi import UploadFile
from datetime import date

from config import FILE_BASE_PATH

import re
import zipfile
import io
import os

class RinexParser:
    
    def __init__(self, file: UploadFile):
        self.save_path = f"{FILE_BASE_PATH}unzipped_files"
        self.file = file
        self.filename = file.filename
        self.timestep = None
        self.radar_coords = None
        self.radar_name = None
        self.date = None
        self.systems = {}
        
    @classmethod
    async def create(cls, file: UploadFile):
        instance = cls(file)
        await instance.process_file()
        return instance
        
    async def process_file(self):
        try:
            self.file = await self.__unzip(self.file)
        except:
            print('file alrady unziped')
            self.file = await self.__newFile(self.file)
        
        with open (self.file, 'r') as f:
            for line in f:
                if line[0] == ">":
                    break

                if self.timestep is None:
                    timestep_match = re.search(r"(\d+\.\d+)\s+INTERVAL", line)
                    if timestep_match:
                        self.timestep = float(timestep_match.group(1).strip())
                
                if self.radar_coords is None:
                    radar_coords_match = re.findall(r"(.*)\s+APPROX POSITION XYZ", line)
                    if radar_coords_match:
                        splited = radar_coords_match[0].split()
                        self.radar_coords = (float(splited[0]), float(splited[1]), float(splited[2]))
                        
                if self.radar_name is None:
                    radar_name_match = re.search(r"(.*)\s+MARKER NAME", line)
                    if radar_name_match:
                        self.radar_name = radar_name_match.group(1).strip()
                
                systems_match = re.findall(r"(.*)\s+SYS / # / OBS TYPES ", line)
                if systems_match:
                    splited = systems_match[0].split()
                    system = f"{splited[0]}_signals".lower()
                    system_types = splited[2:]
                    self.systems[system] = system_types
                    
                if self.date is None:
                    date_match = re.findall(r"(.*)\s+TIME OF FIRST OBS", line)
                    if date_match:
                        splited = date_match[0].split()
                        year, month, day = int(splited[0]), int(splited[1]), int(splited[2])
                        self.date = date(year, month, day)
                    
                
                    
    def get_filepath(self):
        return self.file   
    
    def get_systems(self):
        return self.systems
    
    def get_timestep(self):
        return self.timestep
    
    def get_radar_name(self):
        return self.radar_name
    
    def get_radar_coords(self):
        return self.radar_coords      
    
    def get_date(self):
        return self.date
    
    def get_filename(self):
        return self.filename

        
    async def __newFile(self, file: UploadFile):
        file.file.seek(0)
        file_path = os.path.join(self.save_path, file.filename)
        content = await file.read()
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
        with open(file_path, "wb") as f:
            f.write(content)
            
        return file_path
    
        
    async def __unzip(self, file: UploadFile):
        contents = await file.read()

        with zipfile.ZipFile(io.BytesIO(contents)) as z:
            file_names = z.namelist()

            if len(file_names) == 0:
                raise ValueError("Empty archive")
            elif len(file_names) > 1:
                raise ValueError("Multiple files")
            else:
                file_path = z.extract(file_names[0], self.save_path)

        return file_path
    