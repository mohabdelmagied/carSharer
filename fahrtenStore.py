from datetime import datetime


import connect


class Fahrten:

    def __init__(self):
        self.conn = connect.DBUtil().getExternalConnection()
        self.conn.jconn.setAutoCommit(False)
        self.complete = None

    def get_reserved_rides(self, id):
        """Returns all reserved rides for the current user id"""
        try:
            cursor = self.conn.cursor()
            sql_rides_id = f"SELECT f.startort, f.zielort, f.status, f.fahrtkosten, f.fid, f.transportmittel  FROM reservieren r JOIN fahrt f ON f.fid = r.fahrt AND r.kunde = ?"
            cursor.execute(sql_rides_id, [id])
            result = cursor.fetchall()
            return [{"startort": val[0], "zielort": val[1], "status": val[2], "fahrtkosten": val[3], "fid": val[4], "bid":id, "transportmittel":val[5]} for val in result]
        except Exception as e:
            print(e)
            return False

    def get_open_rides(self, id):
        """Returns all open rides for the current user id"""
        try:
            cursor = self.conn.cursor()
            sql_rides = f"SELECT f.startort, f.zielort, f.status, f.fahrtkosten, f.maxPlaetze, f.fid,f.transportmittel FROM fahrt f"
            cursor.execute(sql_rides)
            result = cursor.fetchall()
            query1="select r.anzPlaetze from reservieren r where r.fahrt=?"
            for j, val in enumerate(result):
                cursor.execute(query1,[val[5]])
                result[j] += (val[4]-sum([i[0] for i in cursor.fetchall()]), )
            return [{"startort": val[0], "zielort": val[1], "status": val[2], "fahrtkosten": val[3], "anzPlaetze":val[-1], "fid":val[5], "bid":id,"transportmittel":val[6]} for val in result]
        except Exception as e:
            print(e)
            return False

    def bestDriver(self,bid):
        """Returns the best driver with the best average rating"""
        try:
            curs = self.conn.cursor()
            query1 = """SELECT avgR, anbieter FROM (select max(avgRate) as avgR FROM (select f.anbieter as anbieter,avg(b.rating) as avgRate
                    from fahrt f,bewertung b,schreiben s
                    where s.fahrt=f.fid and
                    s.bewertung=b.beid group by f.anbieter)) as t1 LEFT JOIN
                    (select f.anbieter as anbieter,avg(b.rating) as avgRate
                    from fahrt f,bewertung b,schreiben s
                    where s.fahrt=f.fid and
                    s.bewertung=b.beid group by f.anbieter) as t2 ON t1.avgR = t2.avgRate
                    """
            curs.execute(query1)
            result1 = curs.fetchall()
            query2 = """select f.transportmittel,f.fid,f.startort,f.zielort,b.email from fahrt f,benutzer b where f.anbieter=? and f.status='offen' and b.bid = ?"""
            curs.execute(query2, [result1[0][1], result1[0][1]])
            result2 = curs.fetchall()
            email = result2[0][4]
            return [{"transportmittel": val[0], "fid": val[1], "startort": val[2], "zielort": val[3], "email": email,
                     "avgRating": result1[0][0], 'bid': bid} for val in result2]
        except Exception as e:
            print(e)
            return False

    def get_ride(self, id):
        """Returns the drive for the given fid"""
        try:
            cursor = self.conn.cursor()
            sql_ride = f"SELECT f.fid, f.startort, f.zielort, f.fahrtdatumzeit, f.maxPlaetze,f.fahrtkosten, f.status, f.anbieter, f.transportmittel, f.beschreibung FROM fahrt f WHERE f.fid = ?"
            cursor.execute(sql_ride, [id])
            result = cursor.fetchall()
            return [{"fid": val[0], "startort": val[1], "zielort": val[2], "fahrtdatumzeit": val[3], "maxPlaetze": val[4], "fahrtkosten": val[5],
                     "status": val[6], "anbieter": val[7], "transportmittel": val[8], "beschreibung": val[9]} for val in result]
        except Exception as e:
            print(e)
            return False
    def set_ride(self, values):
        """Sets the drive with the given values of a values dict"""
        try:
            cursor = self.conn.cursor()
            sql_ride = """insert into fahrt (startort , zielort, fahrtdatumzeit, maxPlaetze, 
            fahrtkosten, status, anbieter, transportmittel, beschreibung)
                        values (? , ? , ?, ?, ?, ?, ?, ?, ?)"""
            timestamp = values["fahrtdatum"].replace(".", "-") + "-" + values["fahrtzeit"].replace(":", ".") + ".00.000000"
            cursor.execute(sql_ride, [values['von'], values['nach'], timestamp,
                           values['maxKap'], values['fahrtkosten'], 'offen', values['id'],
                           values['transportmittel'], values['beschreibung']])
            return True
        except Exception as e:
            print(e)
            return False

    def viewDrive(self, fid, bid):
        """Returns the details of a selected drive by a given user"""
        try:
            curs = self.conn.cursor()
            query = """select f.transportmittel,b.email,f.fahrtdatumzeit,f.startort,f.zielort,f.maxPlaetze,f.fahrtkosten,f.status, cast(f.beschreibung as varchar(500))
                     from fahrt f,transportmittel t,benutzer b
                     where f.fid=? and f.anbieter=b.bid and f.transportmittel=t.tid """
            curs.execute(query, [fid])
            result = curs.fetchall()
            query1 = """select r.anzPlaetze from reservieren r where r.fahrt=?"""
            curs.execute(query1, [fid])
            result1 = curs.fetchall()
            sum = 0
            for reservation in result1:
                sum += reservation[0]
            if result:
                fahrt = {"transportmittel": result[0][0], "anbieter": result[0][1], "fahrtdatumzeit": result[0][2],
                         "startort": result[0][3], "zielort": result[0][4],
                         "freiePlaetze": result[0][5] - sum, "fahrtkosten": result[0][6], "status": result[0][7],
                         "beschreibung": result[0][8], "fid": fid, "bid": bid}
                return fahrt
        except Exception as e:
            print(e)
            return False

    def is_ersteller(self,fid,bid):
        """Returns if the given bid is the creator of the drive with the given fid"""
        try:
            curs=self.conn.cursor()
            query="""select f.fid,f.anbieter from fahrt f where fid=? and anbieter=?"""
            curs.execute(query,[fid,bid])
            result=curs.fetchall()
            return bool(result)
        except Exception as e:
            print(e)
            return False

    def reserveDrive(self,fid,bid,anzahl):
        """Reserves the drive fid by the user bid with amount of reserved places anzahl"""
        try:
            curs=self.conn.cursor()
            update="""insert into reservieren(kunde,fahrt,anzPlaetze)
                            values(?,?,?)"""
            curs.execute(update,[bid,fid,anzahl])
            return True
        except Exception as e:
            print(e)
            return False

    def is_reserved(self,fid,bid):
        """Checks if bid has reserved the drive fid"""
        try:
            curs=self.conn.cursor()
            query="""select r.* from reservieren r where fahrt=? and kunde=?"""
            curs.execute(query,[fid,bid])
            result=curs.fetchall()
            return bool(result)
        except Exception as e:
            print(e)
            return False

    def getRatings(self, fid):
        """Selects the rating of the drive fid"""
        try:
            curs = self.conn.cursor()
            query = """select b.beid,cast(b.textnachricht as varchar(1000)),b.erstellungsdatum,b.rating from bewertung b,schreiben s where s.fahrt=? and s.bewertung=b.beid"""
            curs.execute(query, [fid])
            results = curs.fetchall()
            ratings = {"beid": [], "textnachricht": [], "erstellungsdatum": [], "rating": [], "avg_rating": 0}
            avg_rating = 0
            for result in results[::-1]:
                ratings["beid"].append(result[0])
                ratings["textnachricht"].append(result[1])
                ratings["erstellungsdatum"].append(result[2])
                ratings["rating"].append(result[3])
                avg_rating += int(result[3])
            if ratings["beid"]:
                avg_rating = avg_rating / len(ratings["beid"])
                ratings["avg_rating"] = avg_rating
            return ratings
        except Exception as e:
            print(e)
            return False

    def deleteDrive(self, fid):
        """Deletes the drive and all referenced keys for the drive fid"""
        try:
            curs = self.conn.cursor()
            ratings = self.deleteRating(fid)
            update1 = """delete from bewertung where beid=?"""
            if ratings:
                for rating in ratings:
                    curs.execute(update1, [rating])
            update2 = """delete from reservieren where fahrt=?"""
            curs.execute(update2, [fid])
            update3 = """delete from schreiben where fahrt=?"""
            curs.execute(update3, [fid])
            update4 = """delete from fahrt where fid=?"""
            curs.execute(update4, [fid])
            return True
        except Exception as e:
            print(e)
            return False


    def deleteRating(self, fid):
        """Helper function to get the ratings of fid, to then delete the drive in deleteDrive"""
        try:
            curs = self.conn.cursor()
            query = """select b.beid from bewertung b,schreiben s where s.fahrt=? and s.bewertung=b.beid """
            curs.execute(query, [fid])
            rows = curs.fetchone()
            if rows == None:
                return False
            result = curs.fetchall()
            return result
        except Exception as e:
            print(e)
            return False

    def new_rating(self, bid, bewetungtext, bewertung, fid):
        """Inserts a new rating into the database"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d-%H.%M.%S.%f')
            print(timestamp)
            curs = self.conn.cursor()
            sqlExample = "INSERT INTO bewertung (textnachricht, rating) VALUES(?, ?)"
            curs.execute(sqlExample, [bewetungtext, bewertung])
            curs = self.conn.cursor()
            sql_get_rating = "SELECT b.beid FROM bewertung b"
            curs.execute(sql_get_rating)
            results = curs.fetchall()
            curs = self.conn.cursor()
            sqlExample = "INSERT INTO schreiben (benutzer , fahrt , bewertung) VALUES(?, ?, ?)"
            curs.execute(sqlExample, [bid, fid, results[-1][0]])
            return True
        except Exception as e:
            print(e)
            return False

    def get_available_rides(self, parameters):
        """Returns all available drives for the given parameters"""
        try:
            cursor = self.conn.cursor()
            timestamp_string = parameters['datum'].replace("T", "-") + ".00.000000"
            if parameters["startort"] and parameters["zielort"] and parameters["datum"]:
                sql_ride = f"SELECT f.fid, f.startort, f.zielort, f.fahrtkosten, f.status, f.beschreibung, f.transportmittel FROM fahrt f WHERE f.startort = ? and f.zielort = ? and f.fahrtdatumzeit > ? and f.status='offen'"
                cursor.execute(sql_ride, [parameters['startort'], parameters['zielort'], timestamp_string])
            elif parameters["startort"] and parameters["datum"]:
                sql_ride = f"SELECT f.fid, f.startort, f.zielort, f.fahrtkosten, f.status, f.beschreibung, f.transportmittel FROM fahrt f WHERE f.fahrtdatumzeit > ? and f.status='offen' and f.startort LIKE ? "
                cursor.execute(sql_ride, [timestamp_string, parameters['startort'] + "%"])
            print(parameters['startort'] + "%")
            result = cursor.fetchall()
            return [{"fid": val[0], "startort": val[1], "zielort": val[2], "fahrtkosten": val[3],
                     "status": val[4], "beschreibung": val[5], "transportmittel": val[6], "bid": parameters["id"]} for
                    val in result]
        except Exception as e:
            print(e)
            return False

    def check_rating(self, benutzer_id, Fahrt_id):
        """Checks if benutzer_id already rated a fahrt with fahrt_id"""
        try:
            curs = self.conn.cursor()
            sqlExample = "select * from schreiben where benutzer = ? and fahrt = ?"
            curs.execute(sqlExample, [benutzer_id, Fahrt_id])
            result = curs.fetchall()
            if result:
                return True
            return False
        except Exception as e:
            print(e)
            return False



    def completion(self):
        self.complete = True


    def close(self):
        if self.conn is not None:
            try:
                if self.complete:
                    self.conn.commit()
                else:
                    self.conn.rollback()
            except Exception as e:
                print(e)
            finally:
                try:
                    self.conn.close()
                except Exception as e:
                    print(e)

