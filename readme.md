# READ ME

## GitHub link: https://github.com/Scout2424/LucrareLicenta_BachelorProject.git

## English Variant

**Instructions to use AirNest, Bachelor Degree Project**

#### Raspberry Pi/ hardware part:

- connect Raspberry Pi to monitor/screen (only needed when turning the station on/off, or if one want to access local data from it), internet (upper right corner), power source; connect a keyboard and mouse (can be disconected after starting the station);
- make sure Raspberry Pi is connected to internet (through WIFI or cable)
- go to "sensor_station2026" folder and select file "raspberry_code.py" and run it
- in terminal type the location or skip by pressing enter;
- press the button from the station to start station;
- data is saved locally on "sensor_data_log.csv" (same folder as before)
 
#### Webs Application:

- can be accessed at the following link: https://airnest.duckdns.org/
- on the left side is the navigation bar, from where the pages can be accessed;
- Data page has filter options in order to make the data charts easier to understand;
- Form page has a "Send Message button" at the bottom which sends the form data once completed;
- from Download page the sensor data CSV file and mobile application apk can be downloaded once logged in;
- in the upper right corner there is a "Sign Up" and "Log In" button;
- by pressing "Sign up" button the user will be redirected to the Sign Up page, where the data is to be entered in a form. At the buttom of the form there is a "Create account" button and "Log In" button. When creating an account the user will receive an email from which he needs to press the verify account to have access;
- "Log In" button opens a modal where the data to log in must be entered;
- Log In modal has a "Forgot Password" option, which when pressed, after the mail address is entered, a mail will be given to reset password;
- by loggin in with the admin address the user will have access to the admin page, which has filters for the form data and user activity. There is also a toggle to turn the website in "Maintanance mode".

#### Mobile Application:

- downloaded from the website through apk (Android use only);
- has 4 pages which can be accessed: Home, Data, Predictions, Contact (Form on website). They all have the same functionality as the ones from the website


**Instructions to compile mobile application (if wished to compile locally):**

- open the application folder in Visual Studio Code
- open terminal (make sure the correct directory is selected)
- type in terminal "flutter run"
- select option to run app
- in order to create apk, if not already existent, type in terminal "flutter build apk --release"

The website is hosted on AWS and can be accessed anytime from the following link: https://airnest.duckdns.org/


## Varianta în limba română

**Instrucțiuni de utilizare a AirNest, Proiect de licență**

#### Raspberry Pi/parte hardware:

- conectarea Raspberry Pi la monitor/ecran (necesar doar la pornirea/oprirea stației sau dacă se dorește accesarea datelor locale de pe aceasta), internet (colțul din dreapta sus), sursa de alimentare; conectarea unei tastaturi și a unui mouse (pot fi deconectate după pornirea stației);
- asigurăte că  Raspberry Pi este conectat la internet (prin WIFI sau cablu)
- accesarea folderului „sensor_station2026” și selectarea fișierului „raspberry_code.py” și rularea acestuia;
- în terminal, introduceți locația sau omiteți apăsând Enter;
- apăsați butonul de pe stație pentru a porni stația;
- datele sunt salvate local pe „sensor_data_log.csv” (același folder ca înainte)

#### Aplicație web:

- poate fi accesată la următorul link: https://airnest.duckdns.org/
- în partea stângă se află bara de navigare, de unde se pot accesa paginile;
- Pagina de date are opțiuni de filtrare pentru a face graficele de date mai ușor de înțeles;
- Pagina formularului are un buton „Trimite mesaj” în partea de jos, care trimite datele formularului după completare;
- de pe pagina de descărcare, fișierul CSV cu datele senzorilor și fișierul apk al aplicației mobile pot fi descărcate după conectare;
- în colțul din dreapta sus există butoane „Înregistrare” și „Autentificare”;
- apăsând butonul „Înregistrare”, utilizatorul va fi redirecționat către pagina de înregistrare, unde datele trebuie introduse într-un formular. În partea de jos a formularului există un buton „Creează cont” și un buton „Autentificare”. La crearea unui cont, utilizatorul va primi un e-mail din care trebuie să apese butonul de verificare a contului pentru a avea acces;
- Butonul „Autentificare” deschide o fereastră modală unde trebuie introduse datele de conectare;
- Fereastră modală Autentificare are o opțiune „Am uitat parola”, care, la apăsare, după introducerea adresei de e-mail, va primi un e-mail pentru resetarea parolei;
- prin conectarea cu adresa de administrator, utilizatorul va avea acces la pagina de administrare, care are filtre pentru datele formularului și activitatea utilizatorului. Există, de asemenea, un buton pentru a comuta site-ul web în „Modul de întreținere”.

#### Aplicație mobilă:

- descărcată de pe site prin apk (doar pentru Android);
- are 4 pagini care pot fi accesate: Acasă, Date, Predicții, Contact (Formular pe site). Toate au aceleași funcționalități ca și cele de pe site.

**Instrucțiuni pentru compilarea aplicației mobile (dacă doriți să o compilați local):**

- deschideți folderul aplicației în Visual Studio Code
- deschideți terminalul (asigurați-vă că este selectat directorul corect)
- tastați „flutter run” în terminal
- selectați opțiunea de rulare a aplicației
- pentru a genera un fișier APK (dacă nu există deja), tastați „flutter build apk --release” în terminal


Website-ul este hostat pe AWS și poate să fie accesat oricând de pe următorul link: https://airnest.duckdns.org/