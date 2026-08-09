import pytest
from app import app, db, haversine_km

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

def test_login_page_loads(client):
    response = client.get('/login')
    assert response.status_code == 200

def test_register_page_loads(client):
    response = client.get('/register')
    assert response.status_code == 200

def test_protected_route_redirects_when_not_logged_in(client):
    response = client.get('/citizen-home')
    assert response.status_code == 302

def test_police_map_redirects_when_not_logged_in(client):
    response = client.get('/police-map')
    assert response.status_code == 302

def test_admin_dashboard_redirects_when_not_logged_in(client):
    response = client.get('/admin-dashboard')
    assert response.status_code == 302

def test_haversine_same_point_is_zero():
    distance = haversine_km(28.6139, 77.2090, 28.6139, 77.2090)
    assert distance == 0

def test_haversine_known_distance():
    # Delhi to Mumbai, roughly 1150km apart
    distance = haversine_km(28.6139, 77.2090, 19.0760, 72.8777)
    assert 1100 < distance < 1200