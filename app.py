from flask import Flask, request, Response, abort
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api, Resource
from werkzeug.routing import BaseConverter

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
    in_storage = db.relationship("StorageItem", back_populates="product", lazy=True)

class StorageItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    location = db.Column(db.String(64), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    product = db.relationship("Product", back_populates="in_storage")

class ProductConverter(BaseConverter):
    def to_python(self, value):
        product = Product.query.filter_by(handle=value).first()
        if product is None:
            abort(404, description="Product not found")
        return product

    def to_url(self, value):
        return value.handle

app.url_map.converters['product'] = ProductConverter

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
        
        headers = {"Location": f"/api/products/{product.handle}/"}
        return Response("Product added successfully", status=201, headers=headers)

api.add_resource(ProductCollection, "/api/products/")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
