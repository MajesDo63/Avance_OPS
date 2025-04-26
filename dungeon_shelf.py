from flask import Flask, render_template_string, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import boto3
from uuid import uuid4

# Flask app setup
app = Flask(__name__)
app.secret_key = 'Nicooa6652'

# DynamoDB setup
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
users_table = dynamodb.Table('users')
comics_table = dynamodb.Table('comics')

# CSS
style = """
<style>
  body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; color: #333; text-align: center; }
  .form-container { max-width: 400px; margin: 50px auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
  .form-container input, .form-container button { width: 100%; padding: 10px; margin: 8px 0; border-radius: 6px; border: 1px solid #ccc; }
  .form-container button { background: #3498db; color: #fff; border: none; cursor: pointer; }
  .catalogo { display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; margin: 30px 0; }
  .card { background: #fff; padding: 15px; border-radius: 12px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); width: 200px; }
  .card button { margin-top: 10px; padding: 8px; background: #27ae60; color: #fff; border: none; border-radius: 6px; cursor: pointer; width: 100%; }
  .carrito { max-width: 600px; margin: 30px auto; background: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
  table { width: 100%; border-collapse: collapse; }
  th, td { padding: 10px; border: 1px solid #ddd; }
  th { background: #3498db; color: #fff; }
</style>
"""

# Templates
register_html = style + """
<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>Registro</title></head><body>
  <div class="form-container">
    <h2>Crear Cuenta</h2>
    <form method="post" action="/register">
      <input name="name" type="text" placeholder="Usuario" required>
      <input name="password" type="password" placeholder="Contraseña" required>
      <button type="submit">Registrar</button>
    </form>
    <p>¿Ya tienes cuenta? <a href="/login">Inicia sesión</a></p>
  </div>
</body></html>
"""

login_html = style + """
<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>Login</title></head><body>
  <div class="form-container">
    <h2>Iniciar Sesión</h2>
    <form method="post" action="/login">
      <input name="name" type="text" placeholder="Usuario" required>
      <input name="password" type="password" placeholder="Contraseña" required>
      <button type="submit">Entrar</button>
    </form>
    <p>¿No tienes cuenta? <a href="/register">Regístrate</a></p>
  </div>
</body></html>
"""

main_html = style + """
<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>Catálogo</title></head><body>
  <h1>Bienvenido, {{ session['name'] }}</h1>
  <form action="/logout" method="get"><button>Cerrar sesión</button></form>
  <h2>Catálogo de Cómics</h2>
  <div class="catalogo">
    {% for c in comics %}
    <div class="card">
      <h3>{{ c.issue_name }}</h3>
      <p>Precio: ${{ c.price }}</p>
      <form method="post" action="/agregar_carrito">
        <input type="hidden" name="issue_name" value="{{ c.issue_name }}">
        <input type="hidden" name="price" value="{{ c.price }}">
        <button type="submit">Añadir</button>
      </form>
    </div>
    {% endfor %}
  </div>
  <h2>Carrito</h2>
  <div class="carrito">
    <table>
      <tr><th>Cómic</th><th>Precio</th><th>Cantidad</th></tr>
      {% for item in cart %}
      <tr><td>{{ item.issue_name }}</td><td>${{ item.price }}</td><td>{{ item.quantity }}</td></tr>
      {% endfor %}
    </table>
    <p><strong>Total:</strong> ${{ total }}</p>
  </div>
</body></html>
"""

# Routes
@app.route('/')
def home(): return redirect('/register')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        name = request.form['name']
        pwd  = request.form['password']
        if not name or not pwd:
            return redirect('/register')
        resp = users_table.get_item(Key={'name': name})
        if 'Item' in resp:
            return "Usuario ya existe"
        users_table.put_item(Item={'name': name, 'password': generate_password_hash(pwd)})
        session['name']=name
        session['cart']=[]
        return redirect('/index')
    return render_template_string(register_html)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        name = request.form['name']
        pwd  = request.form['password']
        resp = users_table.get_item(Key={'name': name})
        user = resp.get('Item')
        if user and check_password_hash(user['password'], pwd):
            session['name']=name
            session['cart']=[]
            return redirect('/index')
        return "Credenciales inválidas"
    return render_template_string(login_html)

@app.route('/index')
def index():
    if 'name' not in session: return redirect('/login')
    comics = comics_table.scan().get('Items', [])
    cart   = session.get('cart', [])
    total  = sum(i['quantity']*float(i['price']) for i in cart)
    return render_template_string(main_html, comics=comics, cart=cart, total=f"{total:.2f}")

@app.route('/agregar_carrito', methods=['POST'])
def add_cart():
    issue_name = request.form['issue_name']
    price      = request.form['price']
    cart       = session.get('cart', [])
    for i in cart:
        if i['issue_name']==issue_name:
            i['quantity']+=1
            break
    else:
        cart.append({'issue_name': issue_name,'price':price,'quantity':1})
    session['cart']=cart
    return redirect('/index')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)