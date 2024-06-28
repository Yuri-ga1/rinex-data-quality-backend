from fastapi import FastAPI, UploadFile, HTTPException, File, Form, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from functions import *
from config import *

import os

from parsers.rinex_parser import RinexParser
from parsers.satellite_parser import SatelliteParser


tags_metadata = [
    {
        "name": "default",
        "description": "Operations with load data.",
        "x-auto-generate-in-api-gateway": True,
    },
]

app = FastAPI(openapi_tags=tags_metadata)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ParserManager:
    def __init__(self):
        self.parser: Optional[RinexParser] = None

    async def set_parser(self, rinex_file: UploadFile):
        self.parser = await RinexParser.create(rinex_file)

    def get_parser(self) -> RinexParser:
        if self.parser is None:
            raise HTTPException(status_code=400, detail="Parser not initialized")
        return self.parser

parser_manager = ParserManager()

async def get_parser_manager() -> ParserManager:
    return parser_manager

@app.get("/")
async def welcome():
    return {'status': 'ok'}

# считывает и анализирует данные из файла
@app.post("/upload_data", tags=['default'])
async def upload_data(
    rinexFile: UploadFile = File(...),
    manager: ParserManager = Depends(get_parser_manager)
):
    
    await manager.set_parser(rinexFile)
    parser = manager.get_parser()
    
    systems = parser.get_systems()
    graph_data = get_graph_data(systems)
    
    return JSONResponse(content=graph_data)
    
@app.post("/create_graph_json", tags=['default'])
async def create_graph_json(
    data_period: int = Form(15),
    manager: ParserManager = Depends(get_parser_manager)
):
    parser = manager.get_parser()
    
    date = parser.get_date()
    year = date.year
    yday = str(date.timetuple().tm_yday).zfill(3)
    
    nav_filename = f'BRDC00IGS_R_{year}{yday}0000_01D_MN.rnx.gz'
    rinex_to_csv_processing_id = f"{parser.get_filename()}-_-{nav_filename}"
    cookies = {"rinex_to_csv_processing_id": rinex_to_csv_processing_id}
    
    # print('upload_nav')
    # отправка на сервер файла навигации
    # upload_nav_file(
        # year=year,
        # yday=yday,
        # nav_filename=nav_filename,
        # cookies=cookies
    # )
    # print('upload_rinex')
    # отправка на сервер файла с данными
    # rinex_path = parser.get_filepath()
    # send_file(
        # path=rinex_path,
        # cookies=cookies,
        # url=UPLOAD_RINEX_URL
    # )
    # 
    systems = parser.get_systems()
    # timestep = parser.get_timestep()
    # systems['s_signals'] = []
    # systems['timestep'] = int(timestep)      
    # print(systems)  
    # print('post signals')
    # # отправка сигналов
    # response = requests.post(RUN_URL, json=systems, cookies=cookies)
    # print("get signals")
    # # Получение сигналов
    # response = requests.get(RESULT_URL, cookies=cookies)
    # os.makedirs('result_csv', exist_ok=True)
    save_path = os.path.join(f'{FILE_BASE_PATH}result_csv', 'res.zip')
    # if response.status_code == 200:
        # with open(save_path, 'wb') as f:
            # for chunk in response.iter_content(chunk_size=8192):
                # f.write(chunk)
    # else:
        # response.raise_for_status()
    
    extract_to_folder = f"{FILE_BASE_PATH}satellite\\{year}\\{yday}"
    result={}
    files = unzip_zip(save_path, extract_to_folder=extract_to_folder)    
    # print("create json")
    # for file in files:
        # satellite = await SatelliteParser.create(file)
        # holes = find_holes(satellite, data_period, timestep)
        # result[satellite.get_satellite()] = holes
        
    result=[]
    for file in sorted(files):
        satellite = await SatelliteParser.create(file)
        s={}
        s['id'] = satellite.get_satellite()
        satillite_signals = satellite.get_signals()
        zero_headers = satellite.get_zero_col_headers()
        s["data"] = []
        for signal in satillite_signals:
            y = 'No signal' if signal in zero_headers else 'Complete'
            s['data'].append({
                'x': signal,
                'y': y
            })
        result.append(s)
    # Удаление папки с распакованными файлами
    # if os.path.exists(extract_to_folder):
        # try:
            # shutil.rmtree(extract_to_folder)
        # except OSError as e:
            # print(f"Ошибка при удалении {extract_to_folder}: {e.strerror}")
    # return JSONResponse(content=convert_numpy_to_list(result))
    return JSONResponse(content=result)
    
    
            
if __name__ == "__main__":
    import uvicorn
    uvicorn.run('main:app', host="127.0.0.1", port=8000, reload=True)
    