"""Application entry point."""

import os
from dotenv import load_dotenv
from app.factory import create_app

# Load environment variables
load_dotenv()

# Get configuration from environment
config_name = os.getenv('FLASK_ENV', 'default')

# Create application
app = create_app(config_name)

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )
