from fastapi import FastAPI, UploadFile, BackgroundTasks, HTTPException, File, Form, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from functions import *
from config import *
import uuid
import json
import asyncio

from parsers.satellite_parser import SatelliteParser
from parsers.parser_manager import ParserManager, get_parser_manager

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

@app.get("/")
async def welcome():
    return {'status': 'ok'}

@app.post("/upload_data", tags=['default'])
async def upload_data(
    background_tasks: BackgroundTasks,
    rinexFile: UploadFile = File(...),
    manager: ParserManager = Depends(get_parser_manager)
):
    await manager.set_parser(rinexFile)
    parser = manager.get_parser()
    
    task_id = str(uuid.uuid4())
    
    logger.info(f'Create background task with id: {task_id}')
    redis_client.set(task_id, json.dumps({'status': 'pending'}))
    background_tasks.add_task(download_sattelite_files, parser, task_id)
    
    systems = parser.get_systems()
    graph_data = get_graph_data(systems, task_id)
    content = {
        'task_id': task_id,
        'graph_data': graph_data 
    }
    
    return JSONResponse(content=content)
    
@app.post("/find_holes_in_data", tags=['default'])
async def find_holes_in_data(
    task_id: str = Form(...),
    data_period: int = Form(15),
    manager: ParserManager = Depends(get_parser_manager)
):
    logger.debug(f"Params in find_holes_in_data data_period = {data_period}, task_id = {task_id}")
    task_info = json.loads(redis_client.get(task_id) or '{}')
    
    if not task_info:
        logger.error(f'Something went wrong with background task. Task id: {task_id}')
        raise HTTPException(status_code=404, detail="Files not found.")
    
    while task_info['status'] == 'processing':
        logger.info(f'User waiting for files. Task id: {task_id}')
        await asyncio.sleep(1)
        task_info = json.loads(redis_client.get(task_id) or '{}')
    
    if task_info['status'] == 'failed':
        logger.warning(f"Task processing failed. Task id: {task_id}")
        raise HTTPException(status_code=500, detail="Task processing failed.")
    
    if task_info['status'] == 'completed':
        logger.info(f"Task processing completed. Task id: {task_id}")
        save_path = task_info['result']
    
    
    parser = manager.get_parser()
    
    date = parser.get_date()
    year = date.year
    yday = str(date.timetuple().tm_yday).zfill(3)
    
    timestep = parser.get_timestep()
    
    extract_to_folder = f"{FILE_BASE_PATH}satellite\\{year}\\{yday}"
    result=[]
    files = unzip_zip(save_path, extract_to_folder=extract_to_folder)
    
    logger.debug(f"Creating a response with holes in {parser.filename}")
    for file in files:
        satellite = await SatelliteParser.create(file)
        holes = find_holes(satellite, data_period, timestep)
        
        transformed_data=[]
        for key, value in holes.items():
            signal_holes_dict = {"x": key, "y": value}
            transformed_data.append(signal_holes_dict)
                    
        data={}
        data['id'] = satellite.get_satellite()
        data['data'] = transformed_data
        result.append(data)
        
    return JSONResponse(content=convert_numpy_to_list(result))
    
    
@app.post("/fetch_satellite_info", tags=['default'])
async def get_satellite_data(
    satellite: str = Form(...),
    manager: ParserManager = Depends(get_parser_manager)
):    
    parser = manager.get_parser()
    
    date = parser.get_date()
    year = date.year
    yday = str(date.timetuple().tm_yday).zfill(3)
    
    radar = parser.get_radar_name().lower()
    filename = f'{radar}_{satellite}_{yday}_{year%100}.dat'
    filepath = f'{FILE_BASE_PATH}satellite\\{year}\\{yday}\\{filename}'
    logger.debug(f"Getting data for satellite: {satellite} from file: {filename}")

    _satellite = await SatelliteParser.create(filepath)
    
    signals = _satellite.get_signals()
    data = _satellite.get_data()
    timestep = parser.get_timestep()
    
    if data is None:
        logger.debug("Sattelite file is empty")
        return JSONResponse(content='Empty satellite')
    
    tsn = data[:, 0]
    time = data[:, 1]
    elevation = data[:, 2]
    signals_data = data[:, 4:].T
    
    result={
        'tsn': tsn,
        'seconds': time,
        'elevation': elevation,
        'signals': signals,
        'data': signals_data,
        'timestep': timestep
    }
    
    return JSONResponse(content=convert_numpy_to_list(result))
    
    
    
            
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting app")
    uvicorn.run('main:app', host="0.0.0.0", port=8000, reload=True)
    