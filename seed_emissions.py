import math
import random
from datetime import datetime, timedelta
from app.factory import create_app
from app.extensions import db
from app.models.user import User, UserRole
from app.models.organization import Organization
from werkzeug.security import generate_password_hash
from app.models.emission_activity import EmissionActivity, EmissionScope, ActivityType, ActivityStatus

def generate_data():
    app = create_app()
    with app.app_context():
        print("Starting dummy data generation...")
        
        orgs = Organization.query.all()
        if not orgs:
            print("No organizations found! Create an organization first.")
            return

        scopes = list(EmissionScope)
        types = list(ActivityType)
        statuses = [ActivityStatus.DRAFT, ActivityStatus.SUBMITTED, ActivityStatus.VALIDATED, ActivityStatus.AUDITED]
        
        categories_map = {
            EmissionScope.SCOPE_1: ['Company Vehicles (Fuel)', 'Stationary Combustion (Gas)', 'Fugitive Emissions (Refrigerants)'],
            EmissionScope.SCOPE_2: ['Purchased Electricity', 'Purchased Heating', 'Purchased Cooling'],
            EmissionScope.SCOPE_3: ['Business Travel (Flights)', 'Employee Commuting', 'Waste Generated in Operations', 'Purchased Goods', 'Upstream Transportation']
        }

        today = datetime.now()
        one_year_ago = today - timedelta(days=365)

        total_created = 0

        for org in orgs:
            print(f"Processing organization: {org.name}")
            
            # Get or create a worker for this org to assign activities
            worker = User.query.filter_by(organization_id=org.id, role=UserRole.WORKER).first()
            if not worker:
                print(f"  No worker found for {org.name}. Creating dummy worker.")
                worker = User(
                    email=f"dummy_worker_{org.id}@example.com",
                    first_name="Dummy",
                    last_name="Worker",
                    role=UserRole.WORKER,
                    organization_id=org.id,
                    status="active",
                    password_hash=generate_password_hash('worker123')
                )
                db.session.add(worker)
                db.session.commit()

            # Create 50-80 random emission activities per organization over the last year
            num_activities = random.randint(50, 80)
            
            for _ in range(num_activities):
                # Random date within the last 365 days
                days_ago = random.randint(0, 365)
                start_date = today - timedelta(days=days_ago)
                end_date = start_date + timedelta(days=random.randint(1, 30))

                scope = random.choice(scopes)
                category = random.choice(categories_map[scope])
                act_type = ActivityType.SIMPLE if scope == EmissionScope.SCOPE_2 else random.choice(types)
                
                # Weight towards submitted/validated/audited rather than draft
                status = random.choices(statuses, weights=[10, 20, 40, 30])[0]

                # Generate a realistic-looking CO2e result (in kgCO2e)
                # Let's say between 100kg and 50,000kg
                co2e = round(random.uniform(100.0, 50000.0), 2)
                
                activity = EmissionActivity(
                    organization_id=org.id,
                    created_by_id=worker.id,
                    scope=scope,
                    category=category,
                    activity_type=act_type,
                    description=f"Generated dummy data for {category}",
                    status=status,
                    period_start=start_date.date(),
                    period_end=end_date.date(),
                    co2e_result=co2e,
                    
                    # Dummy ADEME factor data to make it look complete
                    ademe_factor_name=f"Dummy Factor - {category}",
                    ademe_factor_value=random.uniform(0.1, 2.5),
                    ademe_factor_unit=random.choice(['kg', 'kWh', 'liters', 'km']),
                    ademe_factor_source="Base Empreinte (Dummy)",
                )
                
                if act_type == ActivityType.TRANSPORT:
                    activity.distance = round(random.uniform(10, 1000), 2)
                    activity.tonnage = round(random.uniform(1, 40), 2)
                    activity.transport_mode = random.choice(["Road", "Rail", "Sea", "Air"])
                else:
                    activity.quantity = round(random.uniform(100, 10000), 2)
                    activity.quantity_unit = activity.ademe_factor_unit
                
                db.session.add(activity)
                total_created += 1

        db.session.commit()
        print(f"Data generation complete! {total_created} emission activities created.")

if __name__ == '__main__':
    generate_data()
