from fastapi import UploadFile
from datetime import date

from config import FILE_BASE_PATH, logger

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
        
        logger.info(f"Initialized RinexParser for file: {self.filename}")
        
    @classmethod
    async def create(cls, file: UploadFile):
        instance = cls(file)
        logger.info(f"Creating instance for file: {file.filename}")
        await instance.process_file()
        return instance
        
    async def process_file(self):
        try:
            self.file = await self.__unzip(self.file)
            logger.info(f"File unzipped: {self.file}")
        except Exception as e:
            logger.warning(f"File already unzipped or error during unzipping: {e}")
            self.file = await self.__newFile(self.file)
        
        logger.debug(f"Processing file: {self.file}")
        with open (self.file, 'r') as f:
            for line in f:
                if line[0] == ">":
                    break

                if self.timestep is None:
                    timestep_match = re.search(r"(\d+\.\d+)\s+INTERVAL", line)
                    if timestep_match:
                        self.timestep = float(timestep_match.group(1).strip())
                        logger.debug(f"Timestep found: {self.timestep}")
                
                if self.radar_coords is None:
                    radar_coords_match = re.findall(r"(.*)\s+APPROX POSITION XYZ", line)
                    if radar_coords_match:
                        splited = radar_coords_match[0].split()
                        self.radar_coords = (float(splited[0]), float(splited[1]), float(splited[2]))
                        logger.debug(f"Radar coordinates found: {self.radar_coords}")
                        
                if self.radar_name is None:
                    radar_name_match = re.search(r"(.*)\s+MARKER NAME", line)
                    if radar_name_match:
                        self.radar_name = radar_name_match.group(1).strip()
                        logger.debug(f"Radar name found: {self.radar_name}")
                
                systems_match = re.findall(r"(.*)\s+SYS / # / OBS TYPES ", line)
                if systems_match:
                    splited = systems_match[0].split()
                    system = f"{splited[0]}_signals".lower()
                    system_types = splited[2:]
                    self.systems[system] = system_types
                    logger.debug(f"System found: {system} with types {system_types}")
                    
                if self.date is None:
                    date_match = re.findall(r"(.*)\s+TIME OF FIRST OBS", line)
                    if date_match:
                        splited = date_match[0].split()
                        year, month, day = int(splited[0]), int(splited[1]), int(splited[2])
                        self.date = date(year, month, day)
                        logger.debug(f"Date found: {self.date}")
                    
                
                    
    def get_filepath(self):
        logger.debug(f"Returning file path: {self.file}")
        return self.file   
    
    def get_systems(self):
        logger.debug(f"Returning systems: {self.systems}")
        return self.systems
    
    def get_timestep(self):
        logger.debug(f"Returning timestep: {self.timestep}")
        return self.timestep
    
    def get_radar_name(self):
        logger.debug(f"Returning radar name: {self.radar_name}")
        return self.radar_name
    
    def get_radar_coords(self):
        logger.debug(f"Returning radar coordinates: {self.radar_coords}")
        return self.radar_coords      
    
    def get_date(self):
        logger.debug(f"Returning date: {self.date}")
        return self.date
    
    def get_filename(self):
        logger.debug(f"Returning filename: {self.filename}")
        return self.filename

        
    async def __newFile(self, file: UploadFile):
        logger.debug(f"Saving new file: {file.filename}")
        file.file.seek(0)
        file_path = os.path.join(self.save_path, file.filename)
        content = await file.read()
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
        with open(file_path, "wb") as f:
            f.write(content)
            logger.info(f"File saved at: {file_path}")
            
        return file_path
    
        
    async def __unzip(self, file: UploadFile):
        logger.debug(f"Attempting to unzip file: {file.filename}")
        contents = await file.read()

        try:
            with zipfile.ZipFile(io.BytesIO(contents)) as z:
                file_names = z.namelist()

                if len(file_names) == 0:
                    logger.error("Empty archive")
                    raise ValueError("Empty archive")
                elif len(file_names) > 1:
                    logger.error("Multiple files in archive")
                    raise ValueError("Multiple files")
                else:
                    file_path = z.extract(file_names[0], self.save_path)
                    logger.info(f"File extracted to: {file_path}")

            return file_path
        except zipfile.BadZipFile as e:
            logger.error(f"Failed to unzip the file: {e}")
            raise ValueError("Invalid ZIP file")
    