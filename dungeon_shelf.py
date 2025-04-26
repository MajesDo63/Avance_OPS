from flask import Flask, render_template_string, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import boto3
from boto3.dynamodb.conditions import Key

# Flask app setup
app = Flask(__name__)
app.secret_key = 'Nicooa6652'

# DynamoDB setup
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
users_table = dynamodb.Table('users')
comics_table = dynamodb.Table('comics')

# CSS Styles
style = """
<style>
  body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; color: #333; text-align: center; }
  .form-container, .carrito, .catalogo { max-width: 600px; margin: 30px auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
  input, button, select { padding: 8px; margin: 8px 0; border-radius: 4px; border: 1px solid #ccc; }
  button { background: #3498db; color: #fff; cursor: pointer; border: none; }
  .catalogo { display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; }
  .card { width: 200px; }
  .card button { background: #27ae60; width: 100%; }
  .carrito table { width: 100%; border-collapse: collapse; }
  .carrito th, .carrito td { padding: 10px; border: 1px solid #ddd; }
  .carrito th { background: #3498db; color: #fff; }
  .actions { display: flex; gap: 10px; justify-content: center; margin-bottom: 20px; }
</style>
"""

# Templates
register_html = style + """
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>Registro</title></head><body>
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
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>Login</title></head><body>
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
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>Catálogo</title></head><body>
  <h1>Bienvenido, {{ session['name'] }}</h1>
  <div class="actions">
    <form action="/logout" method="get"><button>Cerrar sesión</button></form>
  </div>
  <h2>Catálogo de Cómics</h2>
  <div class="catalogo">
    {% for c in comics %}
    <div class="card">
      <h3>{{ c.issue_name }}</h3>
      <p>Precio: ${{ c.price }}</p>
      <form method="post" action="/agregar_carrito">
        <input type="hidden" name="issue_name" value="{{ c.issue_name }}">
        <input type="hidden" name="price" value="{{ c.price }}">
        <button type="submit">Añadir al carrito</button>
      </form>
    </div>
    {% endfor %}
  </div>
  <h2>Carrito</h2>
  <div class="carrito">
    <table>
      <tr><th>Cómic</th><th>Precio</th><th>Cantidad</th><th>Acciones</th></tr>
      {% for item in cart %}
      <tr>
        <td>{{ item.issue_name }}</td>
        <td>${{ item.price }}</td>
        <td>
          <form method="post" action="/update_cart">
            <input type="hidden" name="issue_name" value="{{ item.issue_name }}">
            <input type="number" name="quantity" value="{{ item.quantity }}" min="1" style="width:60px;">
            <button type="submit">Actualizar</button>
          </form>
        </td>
        <td>
          <form method="post" action="/remove_cart">
            <input type="hidden" name="issue_name" value="{{ item.issue_name }}">
            <button>Eliminar</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </table>
    <form action="/checkout" method="post" style="margin-top:20px;">
      <button style="width:100%; padding:10px; background:#e74c3c;">Comprar Carrito</button>
    </form>
    <p style="margin-top:10px;"><strong>Total:</strong> ${{ total }}</p>
  </div>
</body></html>
"""

# Routes
@app.route('/')
def home():
    return redirect('/register')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        name = request.form['name']; pwd = request.form['password']
        if not name or not pwd: return redirect('/register')
        resp = users_table.query(KeyConditionExpression=Key('name').eq(name))
        if resp.get('Count',0)>0: return "Usuario ya existe"
        users_table.put_item(Item={'name': name, 'password': generate_password_hash(pwd)})
        session['name'], session['cart'] = name, []
        return redirect('/index')
    return render_template_string(register_html)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        name = request.form['name']; pwd=request.form['password']
        resp=users_table.query(KeyConditionExpression=Key('name').eq(name))
        user=next((it for it in resp.get('Items',[]) if check_password_hash(it['password'],pwd)), None)
        if user: session['name'], session['cart'] = name, []; return redirect('/index')
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
    issue_name, price = request.form['issue_name'], request.form['price']
    cart = session.get('cart', [])
    for i in cart:
        if i['issue_name']==issue_name: i['quantity']+=1; break
    else: cart.append({'issue_name': issue_name,'price':price,'quantity':1})
    session['cart']=cart; return redirect('/index')

@app.route('/update_cart', methods=['POST'])
def update_cart():
    issue_name = request.form['issue_name']
    qty = int(request.form['quantity'])
    cart = session.get('cart', [])
    for i in cart:
        if i['issue_name']==issue_name:
            i['quantity'] = qty
            break
    session['cart']=cart; return redirect('/index')

@app.route('/remove_cart', methods=['POST'])
def remove_cart():
    issue_name = request.form['issue_name']
    cart = [i for i in session.get('cart', []) if i['issue_name']!=issue_name]
    session['cart']=cart; return redirect('/index')

@app.route('/checkout', methods=['POST'])
def checkout():
    session['cart']=[]
    return "<h2>Compra realizada con éxito. ¡Gracias!</h2><a href='/index'>Volver al catálogo</a>"

if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

