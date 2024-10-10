from pathlib import Path

import numpy as np
from config import logger

class SatelliteParser:
    
    def __init__(self, file: Path, elevation: int|float = 10):
        self.file = file
        self.filename = file.split('\\')[-1]
        self.elevation = elevation
        self.satellite = None
        self.headers = None
        self.site = None
        self.data = None
        self.zero_col_headers = None
        logger.debug(f"Initializing SatelliteParser for file: {self.file}")
        
    @classmethod
    async def create(cls, file: Path):
        logger.info(f"Creating instance of SatelliteParser for file: {file}")
        instance = cls(file)
        await instance.process_file()
        return instance
    
    async def process_file(self):
        logger.info(f"Processing file: {self.file}")
        data = []
        try:
            with open(self.file, 'r') as f:
                for line in f:
                    if line[0] == '#':
                        splited = line.split()[1:]
                        
                        match splited[0].lower():
                            case 'site:':
                                self.site = splited[1]
                                logger.debug(f"Found site: {self.site} in file {self.file}")
                            case 'satellite:':
                                self.satellite = splited[1]
                                logger.debug(f"Found satellite: {self.satellite} in file {self.file}")
                            case 'columns:':
                                self.headers = splited[1:]
                                logger.debug(f"Headers: {self.headers} in file {self.file}")
                    else:
                        data.append(line.split())
            self.data = np.array(data[1:]).astype(float)
            self.__clean_and_reorder_columns()
        except Exception as e:
            logger.error(f"Error while processing file {self.file}: {e}")
    
    
    def get_data(self):
        return self.data
    
    def get_site(self):
        return self.site
    
    def get_filename(self):
        return self.filename
    
    def get_headers(self):
        return self.headers
    
    def get_zero_col_headers(self):
        return self.zero_col_headers
    
    def get_signals(self):
        return self.headers[4:]
    
    def get_satellite(self):
        return self.satellite
    
    def __hours_to_seconds(self, hour):
        seconds = int(round(hour * 3600))
        return seconds
    
    def __clean_and_reorder_columns(self):
        logger.info("Cleaning and reordering columns based on elevation")
        
        # замена значений на 0 для строк с elevation < 10 начиная с 4 элемента
        mask = self.data[:, 2] <= self.elevation
        logger.debug(f"Cleaning columns with elevation <= {self.elevation} in file {self.file}")
        self.data[mask, 4:] = 0
        
        # найти столбцы, где все значения = 0
        zero_cols = np.all(self.data[:, 4:] == 0, axis=0)
        non_zero_cols = ~zero_cols

        self.zero_col_headers = [self.headers[i + 4] for i in np.where(zero_cols)[0]]
        logger.debug(f"Columns headers without data: {self.zero_col_headers} in file {self.file}")
        
        # создать новый порядок столбцов, перемещая столбцы с нулями в конец
        new_order = np.concatenate((np.arange(4), np.where(non_zero_cols)[0] + 4, np.where(zero_cols)[0] + 4))
        
        # переместить столбцы
        self.data = self.data[:, new_order]
        
        # переместить заголовки
        self.headers = [self.headers[i] for i in new_order]
        
        self.data = self.data[:, :4+non_zero_cols.sum()]
                

        self.data = self.data.T
        if len(self.data) > 4:
            self.data[1] = np.vectorize(self.__hours_to_seconds)(self.data[1])
            self.data = self.data.T
            logger.debug("Converted time to seconds and adjusted data structure")
        else:
            self.data = None
            logger.warning("No data available after cleaning")
            