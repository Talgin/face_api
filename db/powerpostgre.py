import psycopg2
from psycopg2 import sql
from psycopg2.extensions import AsIs
import numpy as np
from shutil import copyfile
from datetime import datetime, timezone


class PowerPost:
    def __init__(self, host, port, dbname, user, pwd):
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.pwd = pwd
        # self.engine = create_engine('postgresql://'+self.user+':'+self.pwd+'@'+self.host+':'+str(self.port)+'/'+self.dbname,echo=False)


    def search_from_persons(self, unique_id):
        try:
            # connect to the PostgresQL database
            conn = psycopg2.connect(host = self.host, port=self.port, dbname=self.dbname, user=self.user, password=self.pwd)
            # create a new cursor object
            cur = conn.cursor()
            # execute the INSERT statement
            cur.execute("SELECT person_name FROM fr.persons WHERE unique_id = {}".format(unique_id))
            blob = cur.fetchone()
            # close the communication with the PostgresQL database
            cur.close()
        except Exception as error:
            print('Error: ' + str(error))
            return None
        finally:
            if conn is not None:
                conn.close()
        return blob


    def search_from_face_db(self, feature, threshold):
        # connect to the PostgresQL database
        # FLAGS.psql_server, FLAGS.psql_server_port, FLAGS.psql_db, FLAGS.psql_user, FLAGS.psql_user_pass
        conn = psycopg2.connect(host=self.host, port=self.port, dbname=self.dbname, user=self.user,
                                password=self.pwd)
        # create a new cursor object
        cur = conn.cursor()
        select_query = '''SELECT fr.faces.unique_id, fr.faces.vector,
                      (CUBE(array[{vector}]) <-> fr.faces.vector) as distance
                      FROM fr.faces
                      ORDER BY (CUBE(array[{vector}]) <-> vector)
                      ASC LIMIT 10'''.format(vector=','.join(str(s) for s in feature),)
        cur.execute(select_query)
        result = cur.fetchall()
        cur.close()
        distance = float(threshold)
        idx = None
        dist = None
        for row in result:
            vec = np.fromstring(row[1][1:-1], dtype=float, sep=',')
            try:
                dist = np.dot(vec,feature)
                if dist > distance:
                    idx = row[0]
            except Exception as error:
                print('Error: ' + str(error))
                return idx, dist
        if idx is not None:
            return idx, dist*100
        else:
            return idx, dist
    

    def one_to_one(self, feature, person_id, threshold):
        # connect to the PostgresQL database
        # FLAGS.psql_server, FLAGS.psql_server_port, FLAGS.psql_db, FLAGS.psql_user, FLAGS.psql_user_pass
        conn = psycopg2.connect(host=self.host, port=self.port, dbname=self.dbname, user=self.user,
                                password=self.pwd)
        # create a new cursor object
        cur = conn.cursor()
        select_query = '''SELECT fr.faces.unique_id, fr.faces.vector,
                      (CUBE(array[{vector}]) <-> fr.faces.vector) as distance
                      FROM fr.faces
                      WHERE unique_id={unique_id}'''.format(vector=','.join(str(s) for s in feature), unique_id=person_id)
        cur.execute(select_query)
        result = cur.fetchall()
        cur.close()
        distance = float(threshold)
        idx = None
        dist = None
        for row in result:
            vec = np.fromstring(row[1][1:-1], dtype=float, sep=',')
            dist = np.dot(vec,feature)
            if dist > distance:
                idx = row[0]
        if idx is not None:
            return idx, dist*100
        else:
            return idx, dist

    
    def insert_new_person(self, unique_id, vector, person_name, person_surname, person_secondname, create_time, group_id, person_iin):
        #try:
        # connect to the PostgresQL database
        conn = psycopg2.connect(host = self.host, port=self.port, dbname=self.dbname, user=self.user, password=self.pwd)
        # create a new cursor object
        cur = conn.cursor()
        # query to be executed
        # current_date
        # insert_query = 
        # query = sql.SQL(insert_query).format(
        #                 unique_id=sql.Identifier(unique_id),
        #                 vector_array=sql.Composable(','.join(str(s) for s in vector)),
        #                 person_name=sql.Literal(person_name),
        #                 person_surname=sql.Literal(person_surname),
        #                 person_secondname=sql.Literal(person_secondname),
        #                 insert_date=sql.Literal(create_time),
        #                 group_id=sql.Literal(group_id),
        #                 person_iin=sql.Literal(person_iin))
        # execute the INSERT statement
        # vector_str = ','.join(str(s) for s in vector)
        vector_str = AsIs('cube(ARRAY[' + str(vector.tolist()).strip('[|]') + '])')
        cur.execute("""
                        WITH 
                            faces_tbl AS
                            (INSERT INTO fr.faces (unique_id, vector) VALUES (%(uid)s, %(vector)s) RETURNING unique_id),
                            persons_tbl AS
                            (INSERT INTO fr.persons (unique_id, person_name, person_surname, person_secondname, insert_date, group_id, person_iin) 
                            VALUES (%(uid)s, %(p_name)s, %(p_surname)s, %(p_sname)s, %(c_time)s, %(g_id)s, %(p_iin)s) RETURNING unique_id)
                        SELECT faces_tbl.unique_id, persons_tbl.unique_id
                        FROM faces_tbl, persons_tbl;
                        """, {'uid': unique_id, 'vector': vector_str, 
                                'p_name': person_name, 'p_surname': person_surname, 
                                'p_sname': person_secondname, 'c_time': create_time, 
                                'g_id': group_id, 'p_iin': person_iin,})
        # commit the changes to the database
        conn.commit()
        # close the communication with the PostgresQL database
        cur.close()
    
        # except Exception as error:
        #     print('Error: ' + str(error))
        #     return False
        # finally:
        #     if conn is not None:
        #         conn.close()
        return True
        

    def insert_into_faces(self, unique_id, vector):
        try:
            # connect to the PostgresQL database
            conn = psycopg2.connect(host = self.host, port=self.port, dbname=self.dbname, user=self.user, password=self.pwd)
            # create a new cursor object
            cur = conn.cursor()
            # execute the INSERT statement
            cur.execute("INSERT INTO fr.faces(unique_id, vector) VALUES ('{}', CUBE(array[{}]))".format(unique_id, ','.join(str(s) for s in vector), ))
            # commit the changes to the database
            conn.commit()
            # close the communication with the PostgresQL database
            cur.close()
        except Exception as error:
            print('Error: ' + str(error))
            return False
        finally:
            if conn is not None:
                conn.close()
        return True


    def delete_from_faces(self, unique_id):
        try:
            # connect to the PostgresQL database
            conn = psycopg2.connect(host = self.host, port=self.port, dbname=self.dbname, user=self.user, password=self.pwd)
            # create a new cursor object
            cur = conn.cursor()
            # execute the INSERT statement
            cur.execute("DELETE FROM fr.faces WHERE unique_id = {}".format(unique_id))
            # commit the changes to the database
            conn.commit()
            # close the communication with the PostgresQL database
            cur.close()
        except Exception as error:
            print('Error: ' + str(error))
            return False
        finally:
            if conn is not None:
                conn.close()
        return True
    
    # unique_id, person_name, person_surname, person_secondname, create_time, group_id
    def insert_into_persons(self, unique_id, person_name, person_surname, person_secondname, create_time, group_id):
        print(unique_id, person_name, person_surname, person_secondname, group_id)
        try:
            # connect to the PostgresQL database
            conn = psycopg2.connect(host=self.host, port=self.port, dbname=self.dbname, user=self.user, password=self.pwd)
            # create a new cursor object
            cur = conn.cursor()
            # execute the INSERT statement
            insert_query = '''INSERT INTO
                    fr.persons(
                    unique_id,
                    person_name,
                    person_surname,
                    person_secondname,
                    create_time,
                    group_id) VALUES (
                    %s,%s,%s,%s,%s,%s
                    )'''
                    # .format(
                    #    unique_id=unique_id,
                    #    person_name=person_name,
                    #    person_surname=person_surname,
                    #    person_secondname=person_secondname,
                    #    create_time=datetime.now(timezone.utc),
                    #    group_id=str(group_id))
            cur.execute(insert_query, (unique_id, person_name, person_surname, person_secondname, create_time, group_id))
            # commit the changes to the database
            conn.commit()
            # close the communication with the PostgresQL database
            cur.close()
        except Exception as error:
            print('Error: ' + str(error))
            return False
        finally:
            if conn is not None:
                conn.close()
        return True


    def delete_from_persons(self, unique_id):
        try:
            # connect to the PostgresQL database
            conn = psycopg2.connect(host = self.host, port=self.port, dbname=self.dbname, user=self.user, password=self.pwd)
            # create a new cursor object
            cur = conn.cursor()
            # execute the INSERT statement
            cur.execute("DELETE FROM fr.persons WHERE unique_id = {}".format(unique_id))
            # commit the changes to the database
            conn.commit()
            # close the communication with the PostgresQL database
            cur.close()
        except Exception as error:
            print('Error: ' + str(error))
            return False
        finally:
            if conn is not None:
                conn.close()
        return True
