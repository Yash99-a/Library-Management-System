from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///library.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer)
    is_available = db.Column(db.Boolean, default=True)

    # Relationship with Loan (book can have many loans)
    loans = db.relationship('Loan', backref='book', lazy=True)

    def __repr__(self):
        return f"Book({self.title}, {self.author})"

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship with Loan (member can have many loans)
    loans = db.relationship('Loan', backref='member', lazy=True)

    def __repr__(self):
        return f"Member({self.name}, {self.email})"

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)

    # Automatically set the end_date to 30 days after the start_date if it's not provided
    @property
    def days_borrowed(self):
        if self.end_date:
            return (self.end_date - self.start_date).days
        return 0

    def __repr__(self):
        return f"Loan(Book ID: {self.book_id}, Member ID: {self.member_id})"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If end_date is not set, automatically set it to 30 days from the start_date
        if not self.end_date:
            self.end_date = self.start_date + timedelta(days=30)


# Routes for Books
@app.route('/books', methods=['GET', 'POST'])
def books():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        genre = request.form['genre']
        year = request.form['year']
        book = Book(title=title, author=author, genre=genre, year=year)
        db.session.add(book)
        db.session.commit()
        return redirect('/books')

    all_books = Book.query.all()
    return render_template('books.html', books=all_books)


@app.route('/books/update/<int:id>', methods=['GET', 'POST'])
def update_book(id):
    book = Book.query.get_or_404(id)
    if request.method == 'POST':
        book.title = request.form['title']
        book.author = request.form['author']
        book.genre = request.form['genre']
        book.year = request.form['year']
        db.session.commit()
        return redirect('/books')

    return render_template('update_book.html', book=book)


@app.route('/books/delete/<int:id>')
def delete_book(id):
    book = Book.query.get_or_404(id)
    db.session.delete(book)
    db.session.commit()

    # Reassign IDs to maintain consecutive numbering
    books = Book.query.all()
    for index, book in enumerate(books, start=1):
        book.id = index
        db.session.add(book)

    db.session.commit()
    return redirect('/books')


@app.route('/books/search', methods=['GET'])
def search_books():
    query = request.args.get('query')
    results = Book.query.filter(
        (Book.title.like(f"%{query}%")) | (Book.id == query)
    ).all()
    return render_template('search_results.html', results=results)


@app.route('/books/borrow/<int:book_id>', methods=['GET', 'POST'])
def borrow_book(book_id):
    book = Book.query.get_or_404(book_id)
    members = Member.query.all()  # Display all members for borrowing selection

    if request.method == 'POST':
        member_id = request.form['member_id']
        member = Member.query.get_or_404(member_id)
        if book.is_available:
            # Create a loan and set the end_date to 30 days from the start_date
            loan = Loan(book_id=book.id, member_id=member.id)
            book.is_available = False  # Mark the book as unavailable
            db.session.add(loan)
            db.session.commit()
            return redirect('/books')

    return render_template('borrow_book.html', book=book, members=members)


@app.route('/books/return/<int:book_id>', methods=['GET', 'POST'])
def return_book(book_id):
    book = Book.query.get_or_404(book_id)
    loan = Loan.query.filter_by(book_id=book.id, end_date=None).first()

    if loan:
        loan.end_date = datetime.utcnow()
        book.is_available = True  # Mark the book as available
        db.session.commit()

    return redirect('/books')


# Routes for Members
@app.route('/members', methods=['GET', 'POST'])
def members():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        member = Member(name=name, email=email)
        db.session.add(member)
        db.session.commit()
        return redirect('/members')

    all_members = Member.query.all()
    return render_template('members.html', members=all_members)


@app.route('/members/update/<int:id>', methods=['GET', 'POST'])
def update_member(id):
    member = Member.query.get_or_404(id)
    if request.method == 'POST':
        member.name = request.form['name']
        member.email = request.form['email']
        db.session.commit()
        return redirect('/members')

    return render_template('update_member.html', member=member)


@app.route('/members/delete/<int:id>')
def delete_member(id):
    member = Member.query.get_or_404(id)
    db.session.delete(member)
    db.session.commit()
    return redirect('/members')


# New Route: Borrowed Books for Each Member
@app.route('/members/<int:id>/borrowed_books')
def borrowed_books(id):
    member = Member.query.get_or_404(id)
    loans = Loan.query.filter_by(member_id=id, end_date=None).all()  # Filter for ongoing loans
    books = [loan.book for loan in loans]  # Get books from the loans
    return render_template('borrowed_books.html', member=member, books=books)


# Home Route
@app.route('/')
def home():
    return render_template('index.html')


if __name__ == "__main__":
    with app.app_context():
        db.create_all()  
    app.run(debug=True, port=8000)
