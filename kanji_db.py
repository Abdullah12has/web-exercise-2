from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

word_components = db.Table(
    "word_components",
    db.Column("word_id", db.Integer, db.ForeignKey("word.id"), primary_key=True),
    db.Column("kanji_id", db.Integer, db.ForeignKey("kanji.id"), primary_key=True)    
)

class Word(db.Model):
    
    id = db.Column(db.Integer, primary_key=True)
    written = db.Column(db.String(32))
    reading = db.Column(db.String(64))
    meaning = db.Column(db.String(256))
    
    kanji_list = db.relationship("Kanji", secondary=word_components, back_populates="words")

    def serialize(self, short_form=False):
        data = {
            "written": self.written,
            "reading": self.reading,
            "meaning": self.meaning
        }
        if not short_form:
            data["kanji_list"] = [kanji.serialize(short_form=True) for kanji in self.kanji_list]
        return data
    
    
class Kanji(db.Model):
    
    id = db.Column(db.Integer, primary_key=True)
    kanji = db.Column(db.String(8))
    meaning = db.Column(db.String(256))
    kunyomi = db.Column(db.String(256), nullable=True)
    onyomi = db.Column(db.String(256), nullable=True)
    strokes = db.Column(db.Integer)
    
    words = db.relationship("Word", secondary=word_components, back_populates="kanji_list")

    def serialize(self, short_form=False):
        data = {
            "kanji": self.kanji,
            "meaning": self.meaning
        }
        if not short_form:
            data.update({
                "kunyomi": self.kunyomi,
                "onyomi": self.onyomi,
                "strokes": self.strokes
            })
        return data


def populate_db():
    k1 = Kanji(
        kanji="配",
        meaning="distribute; spouse; exile; rationing",
        kunyomi="くば.る",
        onyomi="ハイ",
        strokes=10
    )
    k2 = Kanji(
        kanji="列",
        meaning="file; row; rank; tier; column",
        onyomi="レツ;レ",
        strokes=6
    )
    word = Word(
        written="配列",
        reading="はいれつ",
        meaning="1) arrangement; disposition; 2) array (programming)"
    )
    word.kanji_list.append(k1)
    word.kanji_list.append(k2)
    db.session.add(word)
    db.session.commit()
    
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)