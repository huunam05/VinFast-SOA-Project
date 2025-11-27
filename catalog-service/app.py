# catalog-service/app.py

from flask import Flask, request, jsonify, Response
from database import db, CarModel, Inventory
import os
import json
from sqlalchemy import func
from flask_cors import CORS # Thêm CORS
from flask_sqlalchemy import SQLAlchemy

# --- Cấu hình DB và App ---
app = Flask(__name__)
CORS(app) # Kích hoạt CORS
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///catalog_service.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app) # Khởi tạo SQLAlchemy với app

# Khai báo lại Model ở đây (hoặc import từ database.py)

class CarModel(db.Model):
    __tablename__ = 'car_models'
    id = db.Column(db.Integer, primary_key=True) 
    model_name = db.Column(db.String(100), unique=True, nullable=False)
    base_price = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    specs = db.Column(db.Text) 
    inventory_items = db.relationship('Inventory', backref='car', lazy=True)
    def to_dict(self):
        specs_dict = json.loads(self.specs) if self.specs else {} 
        return {
            'id': self.id,
            'model_name': self.model_name,
            'base_price': self.base_price,
            'description': self.description,
            'specs': specs_dict
        }

class Inventory(db.Model):
    __tablename__ = 'inventory'
    id = db.Column(db.Integer, primary_key=True)
    car_model_id = db.Column(db.Integer, db.ForeignKey('car_models.id'), nullable=False) 
    dealer_location = db.Column(db.String(100), nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)

# --- DỮ LIỆU DEMO ---

CARS_DATA_DEMO = [
    {
        "model_name": "VinFast VF 9", "base_price": 1499000000, 
        "description": "SUV điện hạng E, 7 chỗ.", 
        "specs": json.dumps({"motor_type": "Điện", "range": "438 km", "color": "Trắng"}), 
        "inventory_HN": 5, "inventory_HCM": 10
    },
    {
        "model_name": "VinFast VF 8", "base_price": 1057000000, 
        "description": "SUV điện hạng D, 5 chỗ.", 
        "specs": json.dumps({"motor_type": "Điện", "range": "420 km", "color": "Đỏ"}),
        "inventory_HN": 15, "inventory_HCM": 30
    }
]

def create_demo_data(data):
    """Tạo DB và chèn dữ liệu demo."""
    db.create_all()
    
    CarModel.query.delete() 
    Inventory.query.delete()

    for item in data:
        car = CarModel(
            model_name=item['model_name'], 
            base_price=item['base_price'],
            description=item['description'],
            specs=item['specs']
        )
        db.session.add(car)
        
        # Commit tạm thời để lấy ID
        db.session.commit() 
        car_id = car.id
        
        # Thêm dữ liệu tồn kho sử dụng ID mới
        db.session.add(Inventory(car_model_id=car_id, dealer_location="Hà Nội", stock_quantity=item['inventory_HN']))
        db.session.add(Inventory(car_model_id=car_id, dealer_location="TP. HCM", stock_quantity=item['inventory_HCM']))

    db.session.commit() 
    print("Đã khởi tạo DB Danh mục & Kho thành công.")

# --- API ENDPOINTS ---

@app.route('/api/v1/catalog/cars', methods=['GET'])
def get_all_cars():
    cars = CarModel.query.all()
    data = [car.to_dict() for car in cars]
    json_output = app.json.dumps(data, ensure_ascii=False)
    return Response(json_output, mimetype='application/json', status=200)

@app.route('/api/v1/catalog/cars/<int:car_id>', methods=['GET'])
def get_car_details(car_id):
    car = CarModel.query.get(car_id)
    if car:
        data = car.to_dict()
        json_output = app.json.dumps(data, ensure_ascii=False)
        return Response(json_output, mimetype='application/json', status=200)
    return jsonify({"message": "Mẫu xe không tồn tại"}), 404

@app.route('/api/v1/inventory/check', methods=['POST'])
def check_inventory():
    data = request.json
    car_id = data.get('car_id')
    required_quantity = data.get('quantity', 1)
    
    if not car_id:
        return jsonify({"message": "Thiếu ID mẫu xe"}), 400

    total_stock = db.session.query(func.sum(Inventory.stock_quantity)).filter(
        Inventory.car_model_id == car_id
    ).scalar() or 0
    
    is_available = total_stock >= required_quantity
    
    return jsonify({
        "car_id": car_id,
        "is_available": is_available,
        "available_stock": total_stock,
        "required": required_quantity
    }), 200 

# --- CHẠY DỊCH VỤ ---
if __name__ == '__main__':
    with app.app_context():
        db_path = 'catalog_service.db'
        if os.path.exists(db_path):
             os.remove(db_path) 
        create_demo_data(CARS_DATA_DEMO)
            
    print("Catalog Service đang khởi động trên cổng 5002...")
    app.run(port=5002, debug=True)