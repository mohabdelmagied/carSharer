from flask import Flask, request, render_template
import connect
import csv
import re
from fahrtenStore import Fahrten
from datetime import datetime

drive=Fahrten()

app = Flask(__name__, template_folder='template')




def csv_reader(path):
    with open(path, "r") as csvfile:
        tmp = {}
        reader = csv.reader(csvfile, delimiter='=')
        for line in reader:
            tmp[line[0]] = line[1]
    return tmp


config = csv_reader("properties.settings")


@app.route('/carSharer', methods=['GET'])
def carShare():
    try:
        fahrt = Fahrten()
        #setting bid(user)
        id = "2"
        transporter = []
        #To get user's reserved drives
        values_reserved = fahrt.get_reserved_rides(id)
        #To get all open drives
        values_open = fahrt.get_open_rides(id)
    except Exception as e:
        print(e)
    return render_template('carSharer.html', values_reserved=values_reserved, values_open=values_open, id=id)

@app.route("/new_drive", methods=["GET", "POST"])
def new_drive():
    fahrt = Fahrten()
    #In case of GET action
    if request.method == 'GET':
        #getting bid
        id = request.args.get('bid')
        return render_template('new_drive.html', id=id[:-1])
    #In case of POST action
    elif request.method == 'POST':
        values = {}
        #getting drive attributes from user
        values['id'] = request.form.get('id')
        values['von'] = request.form.get('von')
        values['nach'] = request.form.get('nach')
        values['maxKap'] = request.form.get('maxKap')
        values['fahrtkosten'] = request.form.get('fahrtkosten')
        values['fahrtdatum'] = request.form.get('fahrtdatum')
        values['fahrtzeit'] = request.form.get('fahrtzeit')
        values['beschreibung'] = request.form.get('beschreibung')
        values['transportmittel'] = request.form.get('transportmittel')
        values["fahrtzeit"] = request.form.get("fahrtzeit")
        #validating maximum capacity as numeric value and between 0 and 10
        if not values["maxKap"].isnumeric() or (int(values["maxKap"]) <= 0 or int(values['maxKap']) > 10):
            error = "Fehler: Die maximale Kapazität muss einen numerischen Wert haben und zwischen 0 und 10 liegen!"
            return render_template('new_drive.html', error=error,id=values['id'])
        #validating fahrtkosten as numeric and not less than 0
        if not values['fahrtkosten'].isnumeric() or int(values['fahrtkosten']) < 0:
            error = "Fehler: Die Fahrtkosten müssen einen numerischen Wert haben und größer 0 sein!"
            return render_template('new_drive.html', error=error,id=values['id'])
        #validating the length of beschreibung
        if len(values['beschreibung']) > 50:
            error = f"Fehler: Die Länge Beschreibung muss kleiner als 50 Zeichen sein."
            return render_template('new_drive.html', error=error,id=values['id'])
        #getting current time
        curr_time = str(datetime.now())
        idx = curr_time.find(".")
        #validating that the date of the drive is not before the date of its creation
        if values["fahrtdatum"] + " " + values["fahrtzeit"] < str(datetime.now())[:idx-3]:
            error = f"Fehler: Das Datum darf nicht in der Vergangenheit liegen."
            return render_template('new_drive.html', error=error,id=values['id'])
        #Add drive
        response = fahrt.set_ride(values)
        if response:
            fahrt.completion()
            fahrt.close()
            return render_template('new_drive.html', response=response,id=values['id'])
        else:
            error="Fehler: Es ist ein unerwarteter Fehler mit der Datenbank aufgetreten."
            return render_template('new_drive.html', error=error)




@app.route("/view_drive", methods=['GET','POST'])
def view_drive():
    fahrt=Fahrten()
    try:
        dbExists = connect.DBUtil().checkDatabaseExistsExternal()
        #getting bid and fid
        fid = request.args.get('id')
        id=request.args.get('bid')
        fid=fid[:-1]
        id=id[:-1]
        #id = request.args.get('bid')
        if dbExists:
            #get requested drive along with the ratings
            if fahrt.viewDrive(fid, id):
                view_drive=fahrt.viewDrive(fid, id)
                ratings=fahrt.getRatings(fid)
            #In case of POST action
            if request.method == 'POST':
            # convert the post to dictionary
                result = request.form.to_dict()
                #In case the user presses the button to return to homepage
                if "main_page" in result:
                    return render_template("view_main.html")
            #In case user wants to reserve the drive
                if "reservieren" in result:
                    #validating user is not the one who created the drive
                    if fahrt.is_ersteller(fid,id):
                        return render_template("view_drive.html", driveDetails=view_drive, ratings=ratings,message="you cannot reserve this drive because you produced it")
                    #validating that the drive is still open
                    elif view_drive["status"]!="offen":
                        return render_template("view_drive.html", driveDetails=view_drive, ratings=ratings,message="This drive is already closed, you cannot reserve it anymore")
                    #validating that the requested number of seats does not exceed the free number
                    elif int(result["anzahl"])>view_drive["freiePlaetze"]:
                        return render_template("view_drive.html", driveDetails=view_drive, ratings=ratings,message="There is not enough places on this drive for your reservation")
                    #validating that the user didnot already reserve the drive
                    elif fahrt.is_reserved(fid,id):
                        return render_template("view_drive.html", driveDetails=view_drive, ratings=ratings,message="you have already reserved this drive before")
                    else:
                        #reserving drive in db
                        if fahrt.reserveDrive(fid,id,int(result["anzahl"])):
                            fahrt.completion()
                            fahrt.close()
                            return render_template("view_drive.html",driveDetails=view_drive, ratings=ratings,message="you reserved this drive")

                #In case of drive deletion
                if "Loeschen" in result:
                    #validating that the user that deletes the drive is its creator
                    if fahrt.is_ersteller(fid,id):
                        #deleting drive from db
                        if fahrt.deleteDrive(fid):
                            fahrt.completion()
                            fahrt.close()
                            #returning to main page
                            try:
                                fahrt = Fahrten()
                                values_reserved = fahrt.get_reserved_rides(id)
                                values_open = fahrt.get_open_rides(id)
                            except Exception as e:
                                print(e)
                            return render_template('carSharer.html', values_reserved=values_reserved,values_open=values_open, id=id)
                        #showing error message in drive's page if deletion fails
                    else:
                        return render_template("view_drive.html",driveDetails=view_drive,ratings=ratings,message="You cannot delete this drive as you are not its producer")
                #renders the nwe_rating page
                if "bewerten" in result:
                    print("new Rating")
                    return render_template("new_rating.html",fid=fid,bid=id)
            # Get method
            if request.method == 'GET':
                error=""
                #In case drive has no ratings
                if not ratings:
                    return render_template("view_drive.html", driveDetails=view_drive,error="No available ratings")
                return render_template("view_drive.html",driveDetails=view_drive,ratings=ratings)
        raise Exception
    except Exception as e:
        print(e)
        return render_template("view_drive.html",error="Drives are not available")
    finally:
        fahrt.close()

@app.route('/new_rating', methods=["GET",'POST'])
def new_rating():
    message = ""
    fid = request.args.get('id')
    bid = request.args.get('bid')
    fid = fid[:-1]
    bid = bid[:-1]
    try:
        fahrt = Fahrten()
        dbExists = connect.DBUtil().checkDatabaseExistsExternal()
        #In case of POST action
        if dbExists and request.method == "POST":
            result = request.form.to_dict()
            #validating that the user entered comments
            if result["comments"] == "":
                message = "please enter comments"
            #validating the user chose a rating
            elif "rate" not in result:
                message = "please choose rate"
            #validating that the user has not already rated the drive
            elif fahrt.check_rating(bid, fid):
                message = "there is rating already"
            else:
                #rating drive in db
                if fahrt.new_rating(bid, result["comments"], result["rate"], fid):
                    fahrt.completion()
                    message = "successful"
                    fahrt.close()
                else:
                    message = "There was an error with the connection to the database."
    except Exception as e:
        print(e)

    return render_template('new_rating.html', message=message)


@app.route("/view_search", methods=['GET', 'POST'])
def view_search():
    try:
        ride = Fahrten()
        #In case of POST action
        if request.method == 'POST':
            params = {}
            #getting requested drive data
            params['startort'] = request.form.get('startort')
            params['zielort'] = request.form.get('zielort')
            params['datum'] = request.form.get('datum')
            params['id'] = request.form.get('id').replace("/", "")
            """if not params["startort"] or not params["zielort"] or not params["datum"]:
                return render_template('view_search.html', values=params, error="Es darf keine Zeile leer sein.", bid=params["id"])"""
            if not params["startort"] or not params["datum"]:
                return render_template('view_search.html', values=params, error="Es darf keine Zeile leer geben und das Datum muss gesetzt sein.", bid=params["id"])
            #getting drive from db
            available_rides = ride.get_available_rides(params)
            if available_rides:
                return render_template('view_search.html', values=available_rides, bid=params["id"])
            else:
                return render_template('view_search.html', values=params, bid=params["id"], error="Kein Ergebnis gefunden.")
        else:
            bid = request.args.get("id")
            return render_template('view_search.html', values="", bid=bid)
    except Exception as e:
        return render_template('view_search.html', values="")
#Bonus Task
@app.route("/best_drives", methods=["GET"])
def best_drives():
    fahrt = Fahrten()
    #getting drives for highest rated driver
    bid = request.args.get("bid")
    best_drives = fahrt.bestDriver(bid)
    return render_template("best_drives.html", best_drives=best_drives, email=best_drives[0]['email'], avgRating=best_drives[0]['avgRating'])



if __name__ == "__main__":
    port = int("9" + re.match(r"([a-z]+)([0-9]+)", config["username"], re.I).groups()[1])
    app.run(host='0.0.0.0', port=port, debug=True)