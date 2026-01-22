import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.factory import create_app
from app.models.user import User
from flask_login import login_user

def verify_worker_dashboard():
    app = create_app()
    with app.app_context():
        # Get worker user
        worker = User.query.filter_by(email="worker@acme.com").first()
        if not worker:
            print("Worker user not found. Did you seed the database?")
            return False

        with app.test_client() as client:
            # Login
            with client.session_transaction() as sess:
                _id = worker.get_id()
                sess['_user_id'] = _id
                sess['_fresh'] = True

            # Request dashboard
            response = client.get('/dashboard/worker/')
            
            if response.status_code != 200:
                print(f"Failed: Status code {response.status_code}")
                print(response.data.decode())
                return False
            
            content = response.data.decode()
            print(f"DEBUG: Content length: {len(content)}")
            print(f"DEBUG: First 500 chars: {content[:500]}")
            
            checks = [
                "Executive Overview",
                "Total Carbon Footprint",
                "Est. CBAM Liability",
                "Action Center",
                "Recent Data Uploads"
            ]
            
            for check in checks:
                if check not in content:
                    print(f"Failed: '{check}' not found in response")
                    return False
            
            print("Success: Worker dashboard verified!")
            return True

if __name__ == "__main__":
    if not verify_worker_dashboard():
        sys.exit(1)
