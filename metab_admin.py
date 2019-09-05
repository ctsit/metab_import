"""
Metab Admin
Usage:
    python metab_admin.py (-h | --help)
    python metab_admin.py <path_to_config>

Options:
    -h --help   Show this message and exit

Instructions:
    See README

Example:
    $ python metab_admin.py config.yaml
"""
import sys

from flask import Flask, request, flash, redirect, render_template_string
from werkzeug.utils import secure_filename
from yaml import safe_load
import psycopg2
import psycopg2.errorcodes

# Globals
app = Flask(__name__)
conn = None
picture_path = ''

INST_TYPE = 'institute'
DEPT_TYPE = 'department'
LAB_TYPE = 'laboratory'

@app.route('/')
def main_menu():
    return '''
    <!DOCTYPE html>
    <html>
        <head>
            <title>M3C Admin Form</title>
            <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
        </head>
        <body>
            <div class="container mx-auto" style="width: 50%;">
                <div class="row">
                    <h1 class="mx-auto">M3C Admin Form</h1>
                </div>
                <div class="row my-3">
                    <button class="btn btn-info w-100" onclick="window.location.href = '/uploadimage'">Upload Profile Picture</button>
                </div>
                <div class="row my-3">
                    <button class="btn btn-info w-100" onclick="window.location.href = '/createperson'">Create New Person</button>
                </div>
                <div class="row my-3">
                    <button class="btn btn-info w-100" onclick="window.location.href = '/associateperson'">Associate a Person with Inst/Dept/Lab</button>
                </div>
                <div class="row my-3">
                    <button class="btn btn-info w-100" onclick="window.location.href = '/parentorganization'">Modify an Organization's Parent</button>
                </div>
            </div>
        </body>
    </html>
    '''

@app.route('/uploadimage', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        try:
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            picture_file = request.files['picture']
            extension = picture_file.filename.split('.')[-1]
            picture_file.save('{}/'.format(picture_path) + secure_filename('{}_{}.{}'.format(last_name, first_name, extension)))
            flash('Completed save sucessfully')
            return redirect(request.url)
        except Exception:
            flash('Error uploading file')
            return redirect(request.url)

    display_names = []
    cur = conn.cursor()

    cur.execute('SELECT (display_name) from people;')
    rows = cur.fetchall()
    for row in rows:
        display_names.append(row[0])

    return render_template_string('''
    <!doctype html>
    <head>
        <title>Upload a new picture</title>
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
    </head>
    <body>
        <div class="container mx-auto" style="width: 50%;">
            <div class="row">
                <h1 class="mx-auto">Upload new profile picture</h1>
            </div>
            <a href="/">Back to Home</a>
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    {% for message in messages %}
                        <div class="alert alert-warning" role="alert">
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <div class="form-group">
                <label>Search Display Name</label>
                <input id=searchInput class="form-control" list=displaynames name=displayname>
                <datalist id=displaynames>
                    {% for name in dispNameList %}
                        <option value="{{name}}">
                    {% endfor %}
                </datalist>
            </div>

            <form method=post enctype=multipart/form-data>
                <div class="form-group">
                    <label>First Name</label>
                    <input id=firstName class="form-control" type=text name=first_name>
                </div>

                <div class="form-group">
                    <label>Last Name</label>
                    <input id=lastName class="form-control" type=text name=last_name>
                </div>

                <div class="form-group">
                    <input type="file" class="form-control-file" id="inputGroupFile01" name=picture>
                </div>

                <button class="btn btn-primary" type=submit>Upload</button>
            </form>
        </div>
        <script>
            const displayNameInput = document.getElementById('searchInput');
            const displayNames = [...document.getElementById('displaynames').childNodes].filter(name => name.value).map(name => name.value);
            const firstName = document.getElementById('firstName');
            const lastName = document.getElementById('lastName');
            displayNameInput.addEventListener('change', (e) => {
                if (displayNames.includes(e.srcElement.value)) {
                    const splitName = e.srcElement.value.split(' ');
                    firstName.value = splitName[0];
                    lastName.value = splitName[1];
                }
            });
        </script>
    </body>
    ''', dispNameList=display_names)

def associate_and_insert_orgs(cur, institute, department, lab, person_id):
    '''
        Takes in a cursor and creates the association between the id and the different organization types. Creates
        the organization with the right parents if they don't already exist. 
    '''
    inst_id = None
    if institute is not '':
        cur.execute('SELECT id from organizations WHERE name = %s and type = %s', (institute, INST_TYPE))
        rows = cur.fetchall()
        if len(rows) == 0:
            cur.execute('INSERT INTO organizations (name, type) VALUES (%s, %s) RETURNING id', (institute, INST_TYPE))
            inst_id = cur.fetchone()[0]
        elif len(rows) == 1:
            inst_id = rows[0][0]
        else:
            flash('There are more than one Institutions with that name.')
            raise Exception('More that one Institution')
        cur.execute('INSERT INTO associations (organization_id, person_id) VALUES (%s, %s)', (inst_id, person_id))

    if department is not '':
        if inst_id is None:
            flash('Please specify an existing or new Institution for this department')
            raise Exception('Department missing Institution')
        cur.execute('SELECT id FROM organizations WHERE name = %s and type = %s and parent_id = %s', (department, DEPT_TYPE, inst_id))
        rows = cur.fetchall()
        if len(rows) == 0:
            cur.execute('INSERT INTO organizations (name, type, parent_id) VALUES (%s, %s, %s) RETURNING id', (department, DEPT_TYPE, inst_id))
            dept_id = cur.fetchone()[0]
        elif len(rows) == 1:
            dept_id = rows[0][0]
        else:
            pass
            # TODO How do we handle duplicate departments
        cur.execute('INSERT INTO associations (organization_id, person_id) VALUES (%s, %s)', (dept_id, person_id))

    if lab is not '':
        if dept_id is None:
            flash('Please specify an existing or new Department for this lab')
            raise Exception('Lab missing Department')
        cur.execute('SELECT id FROM organizations WHERE name = %s and type = %s and parent_id = %s', (lab, LAB_TYPE, dept_id))
        rows = cur.fetchall()
        if len(rows) == 0:
            cur.execute('INSERT INTO organizations (name, type, parent_id) VALUES (%s, %s, %s) RETURNING id', (lab, LAB_TYPE, dept_id))
            lab_id = cur.fetchone()[0]
        elif len(rows) == 1:
            lab_id = rows[0][0]
        else:
            pass
            # TODO How do we handle duplicate labs
        cur.execute('INSERT INTO associations (organization_id, person_id) VALUES (%s, %s)', (lab_id, person_id))

@app.route('/createperson', methods=['GET', 'POST'])
def create_person():
    cur = conn.cursor()
    institutes = {}
    departments = {}
    labs = {}

    cur.execute('SELECT id, name, type from organizations')
    for row in cur.fetchall():
        if row[2] == INST_TYPE:
            institutes[row[1]] = row[0]
        elif row[2] == DEPT_TYPE:
            departments[row[1]] = row[0]
        elif row[2] == LAB_TYPE:
            labs[row[1]] = row[0]
        else:
            pass
            # what do we do

    cur.close()
    if request.method == 'POST':
        cur = conn.cursor()
        try:
            first_name = request.form['first_name'].strip()
            last_name = request.form['last_name'].strip()
            email = request.form['email'].strip()
            phone = request.form['phone'].strip()
            institute = request.form['institute'].strip()
            department = request.form['department'].strip()
            lab = request.form['lab'].strip()

            if first_name is '' or last_name is '':
                flash('First and last name are required')
                return redirect(request.url)

            cur.execute('INSERT INTO people (display_name, email, phone) VALUES (%s, %s, %s) RETURNING id', (first_name + ' ' + last_name, email, phone))
            person_id = cur.fetchone()[0]
            cur.execute('INSERT INTO names (person_id, first_name, last_name) VALUES (%s, %s, %s)', (person_id, first_name, last_name))

            associate_and_insert_orgs(cur, institute, department, lab, person_id)

            conn.commit()
            flash('Person created successfully')
        except psycopg2.IntegrityError as e:
            conn.rollback()
            if e.pgcode == psycopg2.errorcodes.UNIQUE_VIOLATION:
                flash('First and Last name pair must be unique')
            else:
                print(e)
                flash('Other integrity error')
        except Exception as e:
            print(e)
            conn.rollback()
            flash('Error creating a new person')
        finally:
            cur.close()
        return redirect(request.url)
    
    return render_template_string('''
    <!doctype html>
    <head>
        <title>Create a new Person</title>
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
    </head>
    <body>
        <div class="container mx-auto" style="width: 50%;">
            <div class="row">
                <h1 class="mx-auto">Create a new Person</h1>
            </div>
            <a href="/">Back to Home</a>
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    {% for message in messages %}
                        <div class="alert alert-warning" role="alert">
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            <form method=post enctype=multipart/form-data>
                <div class="form-group">
                    <label>First Name</label>
                    <input class="form-control" type=text name=first_name required>
                </div>

                <div class="form-group">
                    <label>Last Name</label>
                    <input class="form-control" type=text name=last_name required>
                </div>
                
                <div class="form-group">
                    <label>Email</label>
                    <input class="form-control" type=email name=email>
                </div>

                <div class="form-group">
                    <label>Phone Number</label>
                    <input class="form-control" type=tel name=phone>
                </div>

                <div class="form-group">
                    <label>Institute</label>
                    <input class="form-control" list=institutes name=institute>
                    <datalist id=institutes>
                        {% for inst in instituteList %}
                            <option value="{{inst}}">
                        {% endfor %}
                    </datalist>
                </div>

                <div class="form-group">
                    <label>Department</label>
                    <input class="form-control" list=departments name=department>
                    <datalist id=departments>
                        {% for dept in departmentList %}
                            <option value="{{dept}}">
                        {% endfor %}
                    </datalist>
                </div>

                <div class="form-group">
                    <label>Labs</label>
                    <input class="form-control" list=labs name=lab>
                    <datalist id=labs>
                        {% for labItem in labList %}
                            <option value="{{labItem}}">
                        {% endfor %}
                    </datalist>
                </div>

                <button class="btn btn-primary" type=submit>Create Person</button>
            </form>
        </div>
    </body>
    ''', instituteList=institutes.keys(), departmentList=departments.keys(), labList=labs.keys())

@app.route('/associateperson', methods=['GET', 'POST'])
def associate_person():
    display_names = []
    cur = conn.cursor()

    cur.execute('SELECT display_name, email, id from people;')
    rows = cur.fetchall()
    for row in rows:
        display_names.append(str(row[0]) + ' | ' + str(row[1]) + ' | ' + str(row[2]))

    institutes = {}
    departments = {}
    labs = {}

    cur.execute('SELECT id, name, type from organizations')
    for row in cur.fetchall():
        if row[2] == INST_TYPE:
            institutes[row[1]] = row[0]
        elif row[2] == DEPT_TYPE:
            departments[row[1]] = row[0]
        elif row[2] == LAB_TYPE:
            labs[row[1]] = row[0]
        else:
            pass
            # what do we do

    cur.close()
    if request.method == 'POST':
        cur = conn.cursor()
        try:
            person_id = request.form['id'].strip()
            institute = request.form['institute'].strip()
            department = request.form['department'].strip()
            lab = request.form['lab'].strip()

            if person_id is '':
                flash('Please search and select someone')
                return redirect(request.url)
            
            if institute is '' and department is '' and lab is '':
                flash('Please select or enter at least one institute, department, OR lab.')
                return redirect(request.url)

            associate_and_insert_orgs(cur, institute, department, lab, person_id)

            conn.commit()
            flash('Association created successfully')
        except Exception as e:
            print(e)
            conn.rollback()
            flash('Error creating association')
        finally:
            cur.close()
        return redirect(request.url)

    return render_template_string('''
    <!doctype html>
    <head>
        <title>Create a new Person</title>
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
    </head>
    <body>
        <div class="container mx-auto" style="width: 50%;">
            <h1 class="mx-auto">Associate a Person with a Inst/Dept/Lab</h1>
            <a href="/">Back to Home</a>
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    {% for message in messages %}
                        <div class="alert alert-warning" role="alert">
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <div class="form-group">
                <label>Search Display Name</label>
                <input id=searchInput class="form-control" list=displaynames name=displayname>
                <datalist id=displaynames>
                    {% for name in dispNameList %}
                        <option value="{{name}}">
                    {% endfor %}
                </datalist>
            </div>

            <form method=post enctype=multipart/form-data>
                <div class="form-group">
                    <label>Name</label>
                    <input readonly id=name class="form-control" type=text name=name>
                </div>

                <div class="form-group">
                    <label>Email</label>
                    <input readonly id=email class="form-control" type=text name=email>
                </div>

                <input hidden readonly id=id type=text name=id>

                <div class="form-group">
                    <label>Institute</label>
                    <input class="form-control" list=institutes name=institute>
                    <datalist id=institutes>
                        {% for inst in instituteList %}
                            <option value="{{inst}}">
                        {% endfor %}
                    </datalist>
                </div>

                <div class="form-group">
                    <label>Department</label>
                    <input class="form-control" list=departments name=department>
                    <datalist id=departments>
                        {% for dept in departmentList %}
                            <option value="{{dept}}">
                        {% endfor %}
                    </datalist>
                </div>

                <div class="form-group">
                    <label>Labs</label>
                    <input class="form-control" list=labs name=lab>
                    <datalist id=labs>
                        {% for labItem in labList %}
                            <option value="{{labItem}}">
                        {% endfor %}
                    </datalist>
                </div>

                <button class="btn btn-primary" type="submit">Associate Person</button>
            </form>
        </div>
        <script>
            const displayNameInput = document.getElementById('searchInput');
            const displayNames = [...document.getElementById('displaynames').childNodes].filter(name => name.value).map(name => name.value);
            const name = document.getElementById('name');
            const email = document.getElementById('email');
            const id = document.getElementById('id');
            displayNameInput.addEventListener('change', (e) => {
                if (displayNames.includes(e.srcElement.value)) {
                    const splitName = e.srcElement.value.split('|');
                    name.value = splitName[0];
                    email.value = splitName[1];
                    id.value = splitName[2];
                }
            });
        </script>
    </body>
    ''', dispNameList=display_names, instituteList=institutes.keys(), departmentList=departments.keys(), labList=labs.keys())

@app.route('/parentorganization', methods=['GET', 'POST'])
def parent_organization():
    cur = conn.cursor()

    organizations = []

    cur.execute('SELECT id, name, type, parent_id from organizations')
    for row in cur.fetchall():
        organizations.append('{} | {} | {} | {}'.format(row[1], row[2], row[0], row[3]))
    
    if request.method == 'POST':
        cur = conn.cursor()
        try:
            org_id = request.form['orgId'].strip()
            parent_id = request.form['parentId'].strip()

            if org_id is '' or parent_id is '':
                flash('Please select an orgaization')
                return redirect(request.url)

            if parent_id == 'None':
                cur.execute('UPDATE organizations SET parent_id = NULL WHERE id = %s', (org_id))
            else:
                cur.execute('UPDATE organizations SET parent_id = %s WHERE id = %s', (parent_id, org_id))

            conn.commit()
            cur.close()
            flash('Success! Changed Parent ID.')
            return redirect(request.url)
        except Exception as e:
            print(e)
            conn.rollback()
            cur.close()
            flash('Error setting parent')
            return redirect(request.url)

    return render_template_string('''
    <!doctype html>
    <head>
        <title>Modify Organization Parent</title>
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
    </head>
    <body>
        <div class="container mx-auto" style="width: 50%;">
            <h1 class="mx-auto">Modify an Orgaization's Parent</h1>
            <a href="/">Back to Home</a>
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    {% for message in messages %}
                        <div class="alert alert-warning" role="alert">
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <div class="form-group">
                <label>Search Organization to Change</label>
                <input id=searchInput class="form-control" list=orgs name=org>
                <datalist id=orgs>
                    {% for org in orgList %}
                        <option value="{{org}}">
                    {% endfor %}
                </datalist>
            </div>

            <form method=post enctype=multipart/form-data>
                <div class="form-group">
                    <label>Name</label>
                    <input readonly id=orgName class="form-control" type=text name=orgName>
                </div>

                <div class="form-group">
                    <label>Type</label>
                    <input readonly id=orgType class="form-control" type=text name=orgType>
                </div>

                <div class="form-group">
                    <label>Current Parent</label>
                    <input readonly id=currentParent class="form-control" type=text name=currentParent>
                </div>

                <input hidden readonly id=orgId type=text name=orgId>
                <input hidden readonly id=parentId type=text name=parentId>

                <div class="form-group">
                    <label>Search for new Parent</label>
                    <input id=searchInputParent class="form-control" list=parentOrgs name=parentOrg>
                    <datalist id=parentOrgs>
                        {% for org in orgList %}
                            <option value="{{org}}">
                        {% endfor %}
                    </datalist>
                </div>

                <div class="form-group">
                    <label>Parent Name</label>
                    <input readonly id=parentName class="form-control" type=text name=parentName>
                </div>

                <div class="form-group">
                    <label>Parent Type</label>
                    <input readonly id=parentType class="form-control" type=text name=parentType>
                </div>

                <button class="btn btn-primary" type="submit">Make Parent</button>
            </form>
        </div>
        <script>
            const orgSearchInput = document.getElementById('searchInput');
            const organizations = [...document.getElementById('orgs').childNodes].filter(name => name.value).map(name => name.value);
            const orgName = document.getElementById('orgName');
            const orgType = document.getElementById('orgType');
            const orgId = document.getElementById('orgId');
            const currentParent = document.getElementById('currentParent');
            const parentName = document.getElementById('parentName');
            const parentType = document.getElementById('parentType');
            const parentId = document.getElementById('parentId');
            const searchParent = document.getElementById('searchInputParent');
            orgSearchInput.addEventListener('change', (e) => {
                if (organizations.includes(e.srcElement.value)) {
                    const splitName = e.srcElement.value.split('|');
                    orgName.value = splitName[0];
                    orgType.value = splitName[1];
                    orgId.value = splitName[2].trim();
                    parentId.value = splitName[3].trim();
                    if (splitName[3].trim() === 'None') {
                        currentParent.value = 'None';
                    } else {
                        const parent = organizations.find(n => n.split('|')[2].trim() === splitName[3].trim());
                        console.log(parentName);
                        if (parentName) {
                            const splitParentName = parent.split('|');
                            console.log(splitParentName);
                            currentParent.value = parent;
                            parentName.value = splitParentName[0];
                            parentType.value = splitParentName[1].trim();
                            parentId.value = splitParentName[2].trim();
                        } else {

                        }
                    }
                } else {
                    orgName.value = orgType.value = orgId.value = parentName.value = parentType.value = parentId.value = currentParent.value = '';
                }
            });
            searchParent.addEventListener('change', (e) => {
                if (organizations.includes(e.srcElement.value)) {
                    const splitName = e.srcElement.value.split('|');
                    parentName.value = splitName[0].trim();
                    parentType.value = splitName[1].trim();
                    parentId.value = splitName[2].trim();
                }
            });
        </script>
    </body>
    ''', orgList=organizations)

def main():
    '''Sets up a simple website for admin tasks'''
    global conn
    global picture_path

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)

    if sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        sys.exit()

    config_path = sys.argv[1]

    with open(config_path, 'r') as f:
        config_map = safe_load(f)
        picture_path = config_map['picturepath']
        secret_key = config_map['secret']
        db_host = config_map['sup_host']
        db_database = config_map['sup_database']
        db_user = config_map['sup_username']
        db_password = config_map['sup_password']
        db_port = config_map['sup_port']

    try:
        conn = psycopg2.connect(database=db_database, user=db_user, password=db_password, host=db_host, port=db_port)
    except:
        print('Cannot connect to the database')
        sys.exit(-1)

    app.secret_key = secret_key
    app.run()


if __name__ == "__main__":
    main()
