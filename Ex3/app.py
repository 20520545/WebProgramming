from flask import Flask, render_template, request, flash, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import os
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField, StringField, TextAreaField, TelField, IntegerField
from flask_wtf.file import FileRequired, FileAllowed 
from wtforms.validators import InputRequired, ValidationError, Email, NumberRange
from datetime import datetime
import re
from flask_sqlalchemy import SQLAlchemy

# BLOCK CONFIGURATION
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "./static/"
app.config['SECRET_KEY'] = 'SECRETKEY'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
ALLOWED_EXTENSIONS = {'txt'}


# Define the model after the app configuration
class Product(db.Model):
    id = db.Column(db.Integer, nullable=False, primary_key= True)
    title = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(50), nullable=True)
    price = db.Column(db.Integer, nullable=True)
    img = db.Column(db.String, nullable=True)
    number = db.Column(db.Integer,nullable=True)
    def __repr__(self) -> str:
        return f'<Item: {self.title}'

    __table_args__ = (
        db.UniqueConstraint('id', name='unique_id_constraint'),
    )




class UploadForm(FlaskForm):
    file = FileField('File', validators= [
        FileRequired(),
        FileAllowed(['txt','csv'],'Data only!')
    ])
    submit= SubmitField()

class DataForm(FlaskForm):
    def validate_name(form,field):
        if (re.match(field.data, "[a-zA-z ]")):
            raise ValidationError('Name must contain only alphabetical characters.')

    def validate_phone(form,field):
        phone_number = field.data.strip()
        if not (phone_number.startswith('0') and (len(phone_number) == 10 or len(phone_number) == 11) and phone_number.isdigit()):
            raise ValidationError('Invalid phone number. Phone number must start with 0 and be either 10 or 11 digits.')

    name = StringField('Name', validators=[InputRequired(), validate_name])
    email = StringField('Email', validators=[InputRequired(), Email(message="Wrong email format!!!")])
    phone = TelField('Phone', validators=[InputRequired(), validate_phone])
    message = TextAreaField('Message', validators=[InputRequired()])
    submit = SubmitField()

class ProductForm(FlaskForm):
    id = IntegerField('Id', validators=[InputRequired(), NumberRange(min=1)])
    title = StringField('Title', validators=[InputRequired()])
    description = TextAreaField('Description')
    image = FileField('Image (png, jpg)', validators=[InputRequired(message="Please select an image."), 
                                     FileAllowed(['png', 'jpg'], 'Images only!')])
    price = IntegerField('Price', validators=[InputRequired(), NumberRange(min=0)])
    number = IntegerField('Number', validators=[InputRequired(), NumberRange(min=0)])
    submit = SubmitField('Submit')

    def validate_price(self, field):
        if not str(field.data).isdigit() and int(field.data)<0:
            raise ValidationError('Price must be a valid number.')

    def validate_number(self, field):
        if not str(field.data).isdigit() and int(field.data)<0:
            raise ValidationError('Number must be a valid number.')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


with app.app_context():
    db.create_all()
def generate_new_id():
    # Fetch the maximum existing id from the database
    max_id = db.session.query(db.func.max(Product.id)).scalar()

    # If there are no existing products, start with id=1
    if max_id is None:
        return 1

    # Increment the maximum id to generate a new unique id
    return max_id + 1

def update_product_ids_after_delete(deleted_id):
    # Fetch all products with id greater than the deleted id
    products_to_update = Product.query.filter(Product.id > deleted_id).all()

    # Update the ids of the remaining products
    for product in products_to_update:
        product.id -= 1

    db.session.commit()
def HandleData(content:str):
    row= []
    content= content.splitlines()
    for line in content:
        row.append(line.split('|'))
    # Change price format
    for i in range(0,len(row)):
        row[i][2]= '{:,}'.format(int(row[i][2])) + ' VNĐ'
    return row


def parse_file_content(filecontent):
    rows = filecontent.split('\n')
    table_data = []

    for row in rows:
        if row:
            columns = row.split('|')
            columns = [col.strip() for col in columns if col.strip()]
            table_data.append(columns)
    return table_data

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/page/<int:page>", methods=['GET', 'POST'])
def page(page=0):
    if page == 1:
    # try:
        form = UploadForm()
        if request.method == "POST" and form.validate_on_submit():
            file = form.file.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER']+"upload/", filename)
                file.save(filepath)
                print(filepath)
                with open(filepath, 'r') as f:
                    filecontent = f.read()
                    f.close()
                filecontent= HandleData(filecontent)
                print(filecontent)

                return render_template('page1.html', uploaded=True, filename=filename, filecontent=filecontent)
        return render_template('page1.html', uploaded=False, form=form)
    # except Exception as e:
    #     return render_template('index.html')
    elif page == 2:
        form = DataForm()
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        if request.method == "POST" and form.validate_on_submit():
            name = form.name.data
            email = form.email.data
            phone = form.phone.data
            message = form.message.data
            with open('./write/data.txt', 'a') as file:
                file.write(f"{name}|{email}|{phone}|{message}|{dt_string}\n")
                file.close()
            return render_template('page2.html', form=form, send=True, errors=False)
        elif form.errors:
            return render_template('page2.html', form=form, send=False, errors=form.errors)
        return render_template('page2.html', form=form, send=False)
    elif page == 3:
        form = ProductForm()
        action = request.args.get('action')
        product = Product.query.all()

        if action == "create" or action == "edit":
            if request.method == 'POST':
                if form.validate_on_submit():
                    if action == "create":
                        print("Create")
                        new_id = generate_new_id()
                        form.id.data = new_id
                        file = form.image.data
                        filename = secure_filename(file.filename)

                        filepath = os.path.join("./static/upload/", filename)
                        file.save(filepath)
                        print(filepath)
                        item = Product(
                            id=form.id.data,
                            title=form.title.data,
                            description=form.description.data,
                            price='{:,}'.format(int(form.price.data)),
                            img="."+filepath,
                            number=form.number.data
                        )
                        db.session.add(item)
                        db.session.commit()
                        return redirect(url_for('page',page=3))
                    elif action == "edit":
                        id = int(request.args.get("id"))
                        item= db.session.query(Product).filter_by(id=id).first()
                        db.session.delete(item)
                        db.session.commit()
                        update_product_ids_after_delete(id)
                        # id = int(request.form.get("id"))
                        # item= db.session.query(Product).filter_by(id=id).first()
                        # db.session.delete(item)
                        # db.session.commit()
                        # update_product_ids_after_delete(id)
                        # file = form.image.data
                        # filename = secure_filename(file.filename)
                        # filepath = os.path.join("./static/upload/", filename)
                        # file.save(filepath)
                        # item = Product(
                        #     id=form.id.data,
                        #     title=form.title.data,
                        #     description=form.description.data,
                        #     price='{:,}'.format(int(form.price.data)),
                        #     img="."+filepath,
                        #     number=form.number.data
                        # )
                        # db.session.add(item)
                        # db.session.commit()

                        return redirect(url_for('page',page=3))
            return render_template('page3.html', action=action, form=form)

        elif action == "delete":
            id = int(request.args.get("id"))
            item= db.session.query(Product).filter_by(id=id).first()
            db.session.delete(item)
            db.session.commit()
            update_product_ids_after_delete(id)
            return redirect(url_for('page', page=3))
        else:
            return render_template('page3.html', action=action, form=form, product=product)


    else:
        return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
