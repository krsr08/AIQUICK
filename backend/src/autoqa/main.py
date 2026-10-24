import uvicorn
from autoqa.api import create_app
from autoqa.orchestration.service import Service

if __name__ == '__main__':
    uvicorn.run(create_app(Service()), host='127.0.0.1', port=8000, access_log=False, log_level='warning')
