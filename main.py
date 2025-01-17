import math

import pygame as pg
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
import numpy as np
from pygame import Vector3, mouse
import random
from math import atan2
from pygame.math import clamp
from options import shadowQuality, screenWidth, screenHeight, shadowQualityStep


class DynamicLight:
    def __init__(self, _poligons):
      self.poligons = _poligons
      self.points = []

      self.vao = glGenVertexArrays(1)  # tworzymy 1 Vertex Array object - twor ktory sluzy nam do okreslenia layoutu danych wysylanych do gpu
      # oraz podlinkowania tego layoutu do samego bufora z danymi
      glBindVertexArray(self.vao)  # OpenGL dziala jak maszyna stanow, wiec bindujemy vao do ktorego cchemy stworzyc layout oraz bufor danych

      self.vbo = glGenBuffers(1)  # Tworzymy bufor danych - Vertex Buffer Object, ktory bedzie przechowywal dane o wierzcholkach
      glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
      VertexSize = 3 * 4 # 3 floaty po 4 bajty
      VertexCountMax = 2000 #rezerwacja miejsca dla max 2000 punktow w pamieci gpu
      size = VertexSize * VertexCountMax
      glBufferData(GL_ARRAY_BUFFER, size, None, GL_DYNAMIC_DRAW)  # rezerwujemy miejsce dla gpu
      glEnableVertexAttribArray(0)
      glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, VertexSize, ctypes.c_void_p(0))  # Tworzymy layout, czyli informacje o tym, jak GPU powinna odczytywac dane w buforze


    def vector_cross_product(self, A, B):
        x1, y1, z1 = A
        x2, y2, z2 = B

        return Vector3(y1 * z2 - z1 * y2, z1 * x2 - x1 * z2, x1 * y2 - y1 * x2)

    #Tworzymy punkty do sprawdzenia a nastepnie liczymy punkty przeciacia
    def updateVisiblePoints(self, position):
        self.points.clear()

        #dupa = 0
        pointsToCheck = []
        #dla kazdego wierzcholka dodajemy 2 punkty z malym offsetem w lewo i prawo wzgledem promienia od kursora
        #Dla kazdych z tych punktow bedzie trzeba przeprowadzic raycast
        for poligon in self.poligons:
            poligon.visibility = 0.25
            for point in poligon.points:
                toPoint = point - position
                leftToPoint = self.vector_cross_product(Vector3(0.0, 0.0, 1.0), toPoint)
                leftToPoint = leftToPoint.normalize()

             #   dupa += 1
                bias = 0.001
                leftPoint = point + leftToPoint * bias
                rightPoint = point - leftToPoint * bias

                pointsToCheck.append(leftPoint)
                pointsToCheck.append(point)
                pointsToCheck.append(rightPoint)
           # if dupa == 5:
           #    break

        #Sortujemy punkty "kolowo" od lewej do prawej przy pomocy funkcji atan2 - ulatwi to zycie GPU
        pointsToCheck = sorted(
            pointsToCheck,
            key=lambda p: math.atan2((p - position).y, (p - position).x) + math.pi
        )

        bestPoligon = None #zmienna zapisujaca poligon, na ktorym zlapal sie raycast, potrzebny do malego efektu graficznego
        self.points.append(position) #punkt naszej pozycji musi byc startowy, dzieki czemu stworzymy "wachalrz" trojkatow tym samym
                                    #zmniejszamy ilosc wymaganych przesylanych danych do gpu

        #Badamy raycast po poligonach i tworzymy dane do wyslania do gpu by stworzyc dynamiczne oswietlenie 2D
        for point in pointsToCheck:
            toPoint = point - position
            intersection_point = None
            for poligon in self.poligons:
                new_intersection_point = poligon.line_segments_intersection(position, toPoint.normalize())
                if new_intersection_point is not None:
                  if intersection_point is None or position.distance_to(intersection_point) > position.distance_to(new_intersection_point):
                       intersection_point = new_intersection_point
                       bestPoligon = poligon
            if intersection_point is not None:
                self.points.append(intersection_point)
                bestPoligon.visibility = 1.0
            if intersection_point is None:
                print("dupa")
        self.points.append(self.points[1]) #by "wachlarz" trojkatow dzialal poprawnie koniecznei trzeba dodac

    def draw(self):
        #przerabiamy punkty na ciag floatow do zaktualizowania buforu
        vertices = []
        for point in self.points:
            vertices.append(point.x)
            vertices.append(point.y)
            vertices.append(point.z)
        vertices = np.array(vertices, dtype=np.float32)  # tworzymy tablice wierzcholkow, ktora potem bedziemy wysylac do bufora do gpu

        vertexesCount = len(vertices) // 3

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferSubData(GL_ARRAY_BUFFER, 0, vertices.nbytes, vertices) #tym razem modyfikujemy budor wysylajac tylko czesc danych
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLE_FAN, 0, vertexesCount) #drawcall - funckja rysujaca oswietlenie dynamiczne 2D

    def destroy(self):
        vao = (ctypes.c_uint * 1)(self.vao) #funkcje glDelete przyjmuja jako argument adres, a vao i vbo przechowuja same w sobie id buforow
        vbo = (ctypes.c_uint * 1)(self.vbo)

        glDeleteVertexArrays(1, vao)  # Trzeba nastepnie zwolnic pamiec jak w c++ <3
        glDeleteBuffers(1, vbo)
class Poligon:
    def __init__(self, _vertices):

        self.visibility = 0.0
        #z ciagu floatow robimy wierzcholki
        self.points = [Vector3(_vertices[i], _vertices[i + 1], _vertices[i + 2]) for i in range(0, len(_vertices), 3)]

        self.vertices = np.array(_vertices, dtype=np.float32) #tworzymy tablice wierzcholkow, ktora potem bedziemy wysylac do bufora do gpu
        #sa to pokolei koordynaty kazdego kolejnego wierzcholka poligonu: x y z; x y z...
        self.vertexesCount = len(self.vertices)//3 #calkowita ilosc wierzcholkow poligonu

        self.vao = glGenVertexArrays(1) #tworzymy 1 Vertex Array object - twor ktory sluzy nam do okreslenia layoutu danych wysylanych do gpu
        # oraz podlinkowania tego layoutu do samego bufora z danymi
        glBindVertexArray(self.vao) #OpenGL dziala jak maszyna stanow, wiec bindujemy vao do ktorego cchemy stworzyc layout oraz bufor danych

        self.vbo = glGenBuffers(1) #Tworzymy bufor danych - Vertex Buffer Object, ktory bedzie przechowywal dane o wierzcholkach
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, GL_STATIC_DRAW) #Wysylamy wierzcholki do GPU
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * 4, ctypes.c_void_p(0)) #Tworzymy layout, czyli informacje o tym, jak GPU powinna odczytywac dane w buforze

    def destroy(self):
        vao = (ctypes.c_uint * 1)(self.vao) #funkcje glDelete przyjmuja jako argument adres, a vao i vbo przechowuja same w sobie id buforow
        vbo = (ctypes.c_uint * 1)(self.vbo)

        glDeleteVertexArrays(1, vao) #Trzeba nastepnie zwolnic pamiec jak w c++ <3
        glDeleteBuffers(1, vbo)

    #Badamy, czy istnieje kolizja miedzy polprosta a odcinkiem
    def intersection(self, P1, P2, P, Dir):
        #zasada polega na stworzeniu funkcji p(t) i R(r),
        # gdzie dla odcicka t = 0 da nam 1 wierzcholek, a t = 1 da nam 2 wierzcholek (zwykly lerp)
        # zas dla R to zwykla funckja liniowa, gdzie wspolczynnik kierunkowy to Dir i warunek dla x >= 0, bo to polprosta

        #Po stworzeniu ukladu rownan, gdzie R(r) == p(t) dla x i y (2D),mozna uzyskac czy istnieje kolizja i gdzie

        denom = Dir.x * (P2.y - P1.y) - Dir.y * (P2.x - P1.x)
        if denom == 0.0:
            return None  # Brak przecięcia (prosta i polprosta są równoległe)

        # Parametry t i r (parametry odpopwiednio odcinka i prostej)
        t = (Dir.y * (P1.x - P.x) - Dir.x * (P1.y - P.y)) / denom
        r = (P.x * (P1.y - P2.y) + P1.x * (P2.y - P.y) + P2.x * (P.y - P1.y)) / denom

        # Warunki:
        # 1. 0 <= t <= 1 (punkt na odcinku)
        # 2. r >= 0 (punkt na polprostej)
        if 0 <= t <= 1 and r >= 0:
            return Vector3(P.x + r * Dir.x, P.y + r * Dir.y, 0.0)
        return None  # Brak przecięcia

    def line_segments_intersection(self, pos, dir):
        intersections = []

        # z kazdego poligonu robimy liste par jego najblizszych punktow i sprawdzamy raycast
        for i in range(len(self.points)):
            p1 = self.points[i]
            p2 = self.points[(i + 1) % len(self.points)]

            intersectionPoint = self.intersection(p1, p2, pos, dir)
            if intersectionPoint is not None:
                #dodajemy do listy by potem wybrac punkt blizej pozycji kursora
                intersections.append(intersectionPoint)

        #sprawdzamy ktory punkt przeciecia z poligonem jest blizej kursora
        closestIntersection = None
        for intersect in intersections:
            if closestIntersection is None or pos.distance_to(intersect) < pos.distance_to(closestIntersection):
                closestIntersection = intersect

        return closestIntersection
class App:

    #iloczyn wektorowy
    def cross(self, o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def generate_random_polygon(self, num_vertices, x_range=(-1.0, 1.0), y_range=(-1.0, 1.0), z_range=(0.0, 0.0)):
        vertices = []
        for _ in range(num_vertices):
            # Losowanie współrzędnych dla każdego wierzchołka
            x = random.uniform(*x_range)
            y = random.uniform(*y_range)
            z = random.uniform(*z_range)
            vertices.extend([x, y, z])

        # Tworzenie obiektu Poligon
        return Poligon(vertices)

    def __init__(self):
        pg.init() #inicjalizacja pygame
        pg.display.set_mode((screenWidth, screenHeight), pg.OPENGL|pg.DOUBLEBUF) #Flagi - ustawienie rozdzielczosci handlera okna, stworzenie kontekstu dla OpenGl
                                                      # oraz flaga wskazujaca na uzycie podwojnego buforowania
        self.clock = pg.time.Clock() # CHCEMM MIEC 60 FPS BO TAK, WINC POCZEBNE
        glClearColor(0.0, 0.0, 0.0, 1.0) # kolor do czyszczenia bufora koloru w buforze ramki (FBO)

        self.shader = self.createShader("shaders/shader.vert", "shaders/shader.frag")
        self.shader2 = self.createShader("shaders/shader.vert", "shaders/shader2.frag")
        glUseProgram(self.shader) #trzeba zbindowac shader, ktorego chcemy uzywac przy rysowaniu poligonow

        self.poligons = [
                          Poligon([-1.0, -1.0, 0.0,
                                   1.0, -1.0, 0.0,
                                   1.0,  1.0, 0.0,
                                  -1.0,  1.0, 0.0]),

                       # Poligon([-0.2, -0.2, 0.0,
                       #          0.2, -0.2, 0.0,
                       #          0.2, 0.2, 0.0,
                       #          -0.2, 0.2, 0.0]),


                         ]
        #Dodatkowe poligonki dla kazdego, ograniczone pewnym obszarem by sie nie przecinaly
        self.poligons.append(self.generate_random_polygon(3, (-1.0, 0.0), (-1.0, 0.0)))
        self.poligons.append(self.generate_random_polygon(3, ( 1.0, 0.0), (-1.0, 0.0)))
        self.poligons.append(self.generate_random_polygon(3, (-1.0, 0.0), ( 1.0, 0.0)))
        self.poligons.append(self.generate_random_polygon(3, ( 1.0, 0.0), ( 1.0, 0.0)))

        self.dynamicLight = DynamicLight(self.poligons)
        self.mainloop()
    def createShader(self, vertexShaderPath, fragmentShaderPath):
        # Shader - program dzialajacy na GPU, jego kod jest w folderze shaders

        with open(vertexShaderPath, 'r') as f:
            vertexSrc = f.read()
        with open(fragmentShaderPath, 'r') as f:
            fragmentSrc = f.read()

        #Po wczytaniu kodu zrodlowego mozna te programiki skompilowac
        shader = compileProgram(
            compileShader(vertexSrc, GL_VERTEX_SHADER),
            compileShader(fragmentSrc, GL_FRAGMENT_SHADER)
        )

        return shader
    def mainloop(self):
            running = True
            while (running): #Nasza petla glowna
                for event in pg.event.get(): #handler dla szaszej kolejki eventow (zbiera eventy jak: klik myszki, klawiatury, wcisniecie X etc..)
                    if(event.type == pg.QUIT): # Uruchamiane w momencie zamkniecia aplikacji - konczymy glowna petle
                        running = False

                #---------clean----------
                glClear(GL_COLOR_BUFFER_BIT)  # czyscimy zawartosc bufora koloru

                # ---------drawCalls----------
                x_cursor, y_cursor = mouse.get_pos() #pozycja kursora
                # przeksztalcamy do przestrzeni NDC, czyli [-1, 1]
                x_scaled = (2 * x_cursor / screenWidth) - 1
                y_scaled = (2 * y_cursor / screenHeight) - 1
                x_scaled = clamp(x_scaled, -0.999, 0.999)
                y_scaled = clamp(y_scaled, -0.999, 0.999)

                #bindujemy shader do rysowania dynamicznego swiatla 2D
                glUseProgram(self.shader2)

                #Efekt miekkich cieni, metoda na zasadzie (shadowQuality) dodatkowych sampli by zmiekczyc cien
                rads = math.pi/shadowQuality
                repeatUniformLocation = glGetUniformLocation(self.shader2, "uRepeat")
                glUniform1f(repeatUniformLocation, shadowQuality) #komunikacja z karta graficzna i zmiana wartosci danych
                glEnable(GL_BLEND); #wlaczamy blending
                glBlendFunc(GL_ONE, GL_ONE) #funkcja dzieki ktorej zaleznie od kanalu alpha kolory sie akumuluja
                for i in range(shadowQuality):
                    vec = [math.sin(rads * i) * shadowQualityStep, math.cos(rads * i) * shadowQualityStep]
                    self.dynamicLight.updateVisiblePoints(Vector3(x_scaled + vec[0], -y_scaled + vec[1], 0.0))
                    self.dynamicLight.draw()
                glDisable(GL_BLEND);

                #Rysowanie poligonow
                visibilityUniformLocation = glGetUniformLocation(self.shader, "uVisibility")
                glUseProgram(self.shader)
                for i in range(1, len(self.poligons)):
                    poligon = self.poligons[i]
                    glUniform1f(visibilityUniformLocation, poligon.visibility)
                    glBindVertexArray(poligon.vao)  # Związanie VAO poligonu
                    glDrawArrays(GL_TRIANGLE_FAN, 0, poligon.vertexesCount)  # Rysowanie poligonu (trójkąty)

                pg.display.flip() #przerzuc na drugi bufor
                self.clock.tick(60.0) # OTO MOJEM 60 FPS
            self.quit() #zamykamy i czyscimy dane

    def quit(self):
        for poligon in self.poligons:
           poligon.destroy()
        self.dynamicLight.destroy()
        glDeleteProgram(self.shader)
        pg.quit()

if __name__ == "__main__":
    AppObj = App()