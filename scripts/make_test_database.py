import random
import textwrap
from datetime import datetime, timedelta

import pytz

from app import app
from app.invitation import list_missing_invitations
from app.models import Event, Group, GroupMember, Invitation, User, db

tz = pytz.timezone('Europe/Zurich')
random.seed(42)


def create_user(first_name, family_name, role=User.Role.USER):

    username = f'{first_name.lower()}'
    # email = f'{first_name.lower()}.{family_name.lower()}@localhost.com'
    email = 'sqrt93.smtp@gmail.com'
    password = f'{first_name.lower()}-1234'

    user = User(
        username=username,
        first_name=first_name,
        family_name=family_name,
        email=email,
        role=role,
    )
    user.set_password(password)
    db.session.add(user)
    return user


def create_group(name, description):
    group = Group(name=name, description=description)
    db.session.add(group)
    return group


def create_event(name, abstract, description, location, start, end, equipment, cost, deadline, send_invitations, groups):
    event = Event(
        name=name,
        abstract=abstract,
        description=description,
        location=location,
        start=tz.localize(start),
        end=tz.localize(end),
        equipment=equipment,
        cost=cost,
        deadline=tz.localize(deadline),
        send_invitations=send_invitations,
    )
    for group in groups:
        event.groups.append(group)
    db.session.add(event)
    return event


with app.app_context():
    users = [
        create_user('Melissa', 'Foley', role=User.Role.ADMIN),
        create_user('Stephanie', 'Dunlap', role=User.Role.MANAGER),
        create_user('Nicole', 'Parsons'),
        create_user('Michelle', 'Todd'),
        create_user('Heather', 'Bruce'),
        create_user('Jennifer', 'Roberson', role=User.Role.MANAGER),
        create_user('Amanda', 'Jennings'),
        create_user('Amy', 'Villarreal', role=User.Role.MANAGER),
        create_user('Jessica', 'Benson'),
        create_user('Sarah', 'Keller'),
        create_user('Anisa', 'Rodriguez'),
        create_user('Aidan', 'Coffey'),
        create_user('Madeline', 'Burnett'),
        create_user('Charlotte', 'Collier'),
        create_user('Rita', 'Underwood'),
        create_user('Ciara', 'Reynolds'),
        create_user('Summer', 'Sloan'),
        create_user('Willie', 'Russell'),
        create_user('Darcie', 'Roman'),
    ]

    groups = [
        create_group('Teens', 'Für Jungs und Mädels im Alter von 12-16.'),
        create_group('Jugi', '16-20+'),
        create_group('20up', '20+'),
    ]


    today = datetime.now().date()
    today = datetime(today.year, today.month, today.day)

    events = [
        create_event(
            name='Nationalpark-Paket Arenal',
            abstract=textwrap.dedent("""
                Der majestätische Vulkan weist eine konische Form auf – kein Wunder, dass der Vulkan eines der
                beliebtesten Fotomotive Costa Ricas ist. Die Gegend um den Vulkan, die grünen Hänge und
                der tolle Ausblick sind die Highlights des Arenal-Nationalparks."""),
            description=textwrap.dedent("""
                - *1. Tag:* _San José, Tortuguero, Monteverde, Manuel Antonio oder Rincón de la Vieja – Arenal_
                Morgens werden Sie von Ihrem, separat gebuchten Hotel in San José abgeholt und fahren in eine der
                fruchtbarsten Zonen des Landes: die Region von San Carlos. Hier liegt der Vulkan Arenal, der zu
                den aktivsten Vulkanen dieser Erde gehört. Erkunden Sie am Nachmittag die üppige Gartenanlage
                des Hotels oder entspannen Sie in den hoteleigenen Thermalbecken mit Blick auf den Vulkan.

                - *2. Tag:* _Nationalpark Arenal_
                Der Vormittag steht für eigene Aktivitäten zur freien Verfügung. Nachmittags werden Sie für Ihren Ausflug
                zum Vulkan abgeholt. Hier steht zunächst eine ca. 2,5 stündige Wanderung durch vielfältige Flora und Fauna
                auf dem Programm. Zum Abschluss dieses eindrucksvollen Tages können Sie sich bei einem köstliches Abendessen
                verwöhnen lassen. Wieder im Hotel angekommen laden die heissen Thermalbecken zum Relaxen ein.

                - *3. Tag:* _Arenal – San José oder Manuel Antonio, Monteverde, Rincón de la Vieja oder Cabo Blanco_
                Am frühen Vormittag geht es je nach Buchung entweder zurück nach San José oder weiter in einen der
                Nationalparks. 

                Mehr informationen auf: [Kuoni](https://www.kuoni.ch/nord-und-zentralamerika/costa-rica/rundreisen/nationalpark-paket-arenal/)
                """),
            location='Zypern',
            start=today + timedelta(days=-2, hours=18, minutes=30),
            end=today + timedelta(days=-2, hours=22),
            equipment='Taschenlampe',
            cost=0,
            deadline=today + timedelta(days=-4),
            send_invitations=True,
            groups=[groups[0]],
        ),
        create_event(
            name='Wilder Süden',
            abstract=textwrap.dedent("""
                Costa Rica, die „reiche Küste“, ist bekannt für ihre Artenvielfalt in der Tier- und Pflanzenwelt.
                Die Tour führt Sie in den wenig touristischen Süden. Hier finden Sie den grössten Nationalpark und die
                letzten ursprünglichen Regenwälder auf der Pazifikseite Costa Ricas."""),
            description=textwrap.dedent("""
                - *1. Tag:* _San José:_ Begrüssung durch einen Repräsentanten unserer Agentur am Flughafen und Ü
                bergabe der Reiseunterlagen. Transfer zum Hotel Presidente.

                - *2. Tag:* _San José – Vulkan Irazú – Dota:_ Nach dem Frühstück und der Übernahme des Mietwagens haben Sie
                Zeit für einen kleinen Stadtbummel in der Hauptstadt San José. Anschliessend Fahrt auf der Panamericana
                über Cartago hinauf auf die 3.500 Meter hohe „Cordillera de Talamanca“. Unterwegs können Sie einen
                Abstecher zum Nationalpark Irazú mit seinem 3.432 m hohen Vulkan machen. Alternativ bietet sich
                auch ein Besuch des Orosi-Tals mit seiner bekannten Kolonialkirche an. Anschliessend geht es hinauf
                nach Dota, am Nationalpark Los Quetzales gelegen. 1 Nacht in der Sueños del Bosque. `Ca. 90 km`

                - *3. Tag:* _Dota – San Isidro – Biologische Station Las Cruces:_ Am frühen Morgen Gelegenheit zu einer Wanderung.
                Weiter geht es über den „Cerro de la Muerte“, bevor es in Serpentinen zum 2.800 m tiefer gelegenen
                Städtchen San Isidro hinuntergeht. Weiterfahrt ins romantische Tal des Río Grande de Térraba, dem
                wasserreichsten Fluss Costa Ricas. 1 Nacht in der Biologischen Station Las Cruces, der OTS
                (Organization for Tropical Studies) bei San Vito. `Ca. 180 km`

                - *4. Tag:* _Botanischer Garten Wilson – Golfito – La Gamba:_ Nach dem Frühstück haben Sie Gelegenheit,
                den Botanischen Garten Wilson zu besuchen. Machen Sie einen Abstecher zur Grenzstation Cañas Gordas,
                von dort aus haben Sie einen fantastischen Ausblick auf den Vulkan Barú, den einzigen Vulkan Panamas.
                Anschliessend Weiterfahrt über das mehr als 1.000 m tiefer gelegene Städtchen Neilly, dessen Gegend
                von ausgedehnten Ölpalmenplantagen bedeckt ist, nach Golfito. Nach der Ankunft in La Gamba Abendessen
                und 1 Nacht in der Esquinas Rainforest Lodge. `Ca. 100 km`

                Mehr informationen auf: [Kuoni](https://www.kuoni.ch/nord-und-zentralamerika/costa-rica/rundreisen/wilder-sueden/)
                """),
            location='Costa Rica',
            start=today + timedelta(hours=18, minutes=45),
            end=today + timedelta(hours=24),
            equipment='Zelt',
            cost=120,
            deadline=today + timedelta(hours=12),
            send_invitations=True,
            groups=[groups[0], groups[1]],
        ),
        create_event(
            name='Komodo & Flores zum Kennenlernen',
            abstract=textwrap.dedent("""
                Diese Kurzreise bietet eine wunderbare Gelegenheit zwei abwechslungsreiche indonesische Inseln
                kennenzulernen."""),
            description=textwrap.dedent("""
                - *1. Tag:* _Südbali – Labuan Bajo (Flores):_ Frühmorgens Abholung von Ihrem separat gebuchten Hotel in
                Südbali und Transfer zum Flughafen für Ihren Flug nach Labuan Bajo/Westflores.
                Fahrt in das Dorf Melo, wo Sie einer für Sie eigens arrangierten Privataufführung des spektakulären
                „Caci“-Tanzes, auch Peitschtanz genannt, beiwohnen werden. Danach Besuch der Tropfsteinhöhle
                „Batu Cermin”. Nach dem Mittagessen Fahrt nach Labuan Bajo. 3 Nächte im Hotel Bintang Flores. (Mittagessen)

                - *2. Tag:* _Labuan Bajo – Komodo – Labuan Bajo:_ Frühes Frühstück und Transfer zum Hafen. Ca. 2,5
                stündige Bootsfahrt nach Komodo. Ein Park-Ranger wird Sie sodann auf einem ca. 2 km langen
                Trekking-Pfad (insg. 4 km hin und zurück) zur Ranger-Station Banunggulung begleiten, wo Sie die
                faszinierenden Komodo-Warane, die grössten lebenden Echsen der Welt, nun in freier Wildbahn
                beobachten können. Danach Rückkehr zu Ihrem Schiff und Fahrt zum Strand „Pantai Merah” –
                wegen seines rosa-rot leuchtenden Sandes auch Pink Beach genannt. In dieser traumhaften Bucht haben
                 Sie die Möglichkeit zu schwimmen und zu schnorcheln. Mittagessen an Bord des Schiffes, welches
                 Sie zurück nach Labuan Bajo bringt. (`Frühstück`, `Mittagessen`)

                - *3. Tag:* _Labuan Bajo – Insel Rinca – Bidadari Island – Labuan Bajo:_ Nach einem frühen Frühstück
                Transfer zum Hafen von Labuan Bajo für Ihre ca. 2-stündige Schifffahrt zur Insel Rinca.
                Ein Ranger begleitet Sie dann auf einem insgesamt 4 km langen Trekking-Pfad in das Innere der Insel.
                Halten Sie während dieser Wanderung u.a. Ausschau nach Komodo-Waranen, wilden Wasserbüffeln, seltenen
                Vogelarten und Affen. Dauer der Wanderung ca. 2 Std. Rückkehr zum Schiff und Mittagessen.
                Danach geht es weiter nach Bidadari Island, wo Sie nun Gelegenheit haben zu schwimmen oder
                zu schnorcheln. Rückkehr nach Labuan Bajo. (`Frühstück`, `Mittagessen`)

                - *4. Tag:* _Labuan Bajo – Südbali:_ Nach dem Frühstück Transfer zum Flughafen von Labuan Bajo.
                Flug nach Bali und Transfer zu Ihrem separat gebuchten Hotel in Südbali. Ende der Reise. (`Frühstück`)
                
                Mehr informationen auf: <https://www.kuoni.ch/asien/indonesien/rundreisen/komodo-flores-zum-kennenlernen/>
                """),
            location='Südbali​',
            start=today + timedelta(days=7, hours=17, minutes=30),
            end=today + timedelta(days=7, hours=26),
            equipment='Wanderschuhe',
            cost=5,
            deadline=today + timedelta(days=6, hours=12),
            send_invitations=False,
            groups=[groups[2]],
        ),
        create_event(
            name='Flusskreuzfahrt – Mekong Eyes',
            abstract=textwrap.dedent("""
                Mit der Reisbarke „Mekong Eyes” durch das landschaftlich reizvolle und fruchtbare Mekong-Delta.
                Entspannen Sie an Deck und schippern Sie in einem traditionellen Sampan-Boot zu farbenfrohen Märkten."""),
            description=textwrap.dedent("""
                - *1. Tag:* _Saigon – Can Tho – Cai Be_ Am Morgen gegen 07.30 Uhr Abholung von Ihrem Übernachtungshotel
                in Saigon und Transfer zum Pier in Can Tho. Gegen Mittag gehen Sie an Bord.
                Geniessen Sie das Mittagessen, während das Schiff seine Fahrt aufnimmt.
                Entspannen Sie sich an Deck und geniessen Sie fantastische Eindrücke, den
                üppigen Dschungel, kleine Kanäle, den Alltag der Menschen im Mekongdelta.
                Abendessen an Bord. Lassen Sie den Tag während des Sonnenuntergangs über der
                grandiosen Wasserlandschaft ausklingen. Übernachtung an Bord der Mekong Eyes.

                - *2. Tag:* _Cai Be – Saigon_ Am nächsten Tag legt Ihr Schiff bei Sonnenaufgang ab.
                In Cai Rang oder Cai Be steigen Sie auf einen Sampan um und erkunden einen
                schwimmenden Markt mit einer Fülle an Tropenfrüchten, Gemüse und Kunsthandwerk.
                Nach dem Mittagessen ist es Zeit, Abschied vom Mekongdelta zu nehmen. Rücktransfer in Ihr Hotel
                in Saigon, Ankunft am Nachmittag gegen 16.30 Uhr.

                Mehr informationen auf: <https://www.kuoni.ch/asien/vietnam/rundreisen/flusskreuzfahrt-mekong-eyes/>
                """),
            location='Mekong',
            start=today + timedelta(days=14, hours=18, minutes=00),
            end=today + timedelta(days=14, hours=20, minutes=15),
            equipment='Hut',
            cost=10,
            deadline=today + timedelta(days=12),
            send_invitations=False,
            groups=[groups[0]],
        ),
    ]

    for i, user in enumerate(users):
        g1, g2 = random.sample(set(range(len(groups))), 2)

        if random.uniform(0, 1) > 0.3:
            role = GroupMember(user=user, group=groups[g1], role=GroupMember.Role.MEMBER)
            db.session.add(role)

        if random.uniform(0, 1) > 0.3:
            role = GroupMember(user=user, group=groups[g2], role=GroupMember.Role.SPECTATOR)
            db.session.add(role)

    db.session.commit()

    # Pre-populate invitations
#    for invitation in list_missing_invitations():
#        db.session.add(invitation)
    db.session.commit()
