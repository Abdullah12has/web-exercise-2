import json
from datetime import datetime
from flask import Flask, request, abort, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine
from sqlalchemy import event
from flask_restful import Api, Resource
from jsonschema import validate, ValidationError, draft7_format_checker
from werkzeug.exceptions import NotFound, Conflict, BadRequest, UnsupportedMediaType

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
api = Api(app)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

deployments = db.Table("deployments",
    db.Column("deployment_id", db.Integer, db.ForeignKey("deployment.id"), primary_key=True),
    db.Column("sensor_id", db.Integer, db.ForeignKey("sensor.id"), primary_key=True)
)

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    altitude = db.Column(db.Float, nullable=True)
    description = db.Column(db.String(256), nullable=True)
    
    sensor = db.relationship("Sensor", back_populates="location", uselist=False)

class Deployment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    
    sensors = db.relationship("Sensor", secondary=deployments, back_populates="deployments")

class Sensor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False, unique=True)
    model = db.Column(db.String(128), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("location.id"), unique=True)
    
    location = db.relationship("Location", back_populates="sensor")
    measurements = db.relationship("Measurement", back_populates="sensor", cascade="all, delete-orphan")
    deployments = db.relationship("Deployment", secondary=deployments, back_populates="sensors")

class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.Integer, db.ForeignKey("sensor.id", ondelete="SET NULL"))
    value = db.Column(db.Float, nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    
    sensor = db.relationship("Sensor", back_populates="measurements")

    def deserialize(self, data):
        try:
            self.value = float(data["value"])
            self.time = datetime.fromisoformat(data["time"])
        except (KeyError, ValueError):
            raise BadRequest("Invalid measurement data format.")

    @staticmethod
    def json_schema():
        return {
            "type": "object",
            "properties": {
                "time": {"type": "string", "format": "date-time"},
                "value": {"type": "number"}
            },
            "required": ["time", "value"]
        }

class MeasurementCollection(Resource):
    def post(self, sensor):
        if request.content_type != "application/json":
            raise UnsupportedMediaType("Content type must be application/json.")

        sensor_obj = Sensor.query.filter_by(name=sensor).first()
        if not sensor_obj:
            raise NotFound(f"Sensor '{sensor}' not found.")

        try:
            data = request.get_json()
            validate(data, Measurement.json_schema(), format_checker=draft7_format_checker)
            measurement = Measurement(sensor=sensor_obj)
            measurement.deserialize(data)
            db.session.add(measurement)
            db.session.commit()
            location_header = url_for("measurementitem", sensor=sensor, measurement=measurement.id, _external=False) + "/"
            return "", 201, {"Location": location_header, "Content-Type": "text/html", "Content-Length": "0"}
        except ValidationError as e:
            raise BadRequest(str(e))
        except IntegrityError:
            db.session.rollback()
            raise Conflict("Database integrity error.")

class MeasurementItem(Resource):
    def delete(self, sensor, measurement):
        measurement_obj = Measurement.query.get(measurement)
        if not measurement_obj:
            raise NotFound("Measurement not found.")
        db.session.delete(measurement_obj)
        db.session.commit()
        return "", 204

@app.route("/sensors/")
def get_sensors():
    sensors = Sensor.query.all()
    return jsonify([[sensor.name, sensor.model] for sensor in sensors])

api.add_resource(MeasurementCollection, "/api/sensors/<string:sensor>/measurements/")
api.add_resource(MeasurementItem, "/api/sensors/<string:sensor>/measurements/<int:measurement>")

if __name__ == "__main__":
    app.run(debug=True)
