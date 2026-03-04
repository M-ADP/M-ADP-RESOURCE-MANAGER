from http import HTTPStatus

import uvicorn
from src.api import create_app

app = create_app()

@app.get(status_code=HTTPStatus.ACCEPTED)
async def health_check():
    return

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8001)