from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api, Resource

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
api = Api(app)  # Initialize Flask-RESTful

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    handle = db.Column(db.String(80), unique=True, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)

class ProductCollection(Resource):
    def get(self):
        products = Product.query.all()
        return [
            {"handle": p.handle, "weight": p.weight, "price": p.price} for p in products
        ], 200

    def post(self):
        if request.content_type != 'application/json':
            return {"error": "Request content type must be JSON"}, 415
        
        data = request.json
        if not data or "handle" not in data or "weight" not in data or "price" not in data:
            return {"error": "Incomplete request - missing fields"}, 400
        
        if not isinstance(data["weight"], (int, float)) or not isinstance(data["price"], (int, float)):
            return {"error": "Weight and price must be numbers"}, 400
        
        if Product.query.filter_by(handle=data["handle"]).first():
            return {"error": "Handle already exists"}, 409
        
        product = Product(handle=data["handle"], weight=data["weight"], price=data["price"])
        db.session.add(product)
        db.session.commit()
        
        return {"message": "Product added successfully"}, 201

api.add_resource(ProductCollection, "/api/products/")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
