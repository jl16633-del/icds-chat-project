import tkinter
import math
import Point
import Record
import random

class Chess_Board_Canvas(tkinter.Canvas):
    def __init__(self, master=None, height=500, width=500, network_client=None):
        tkinter.Canvas.__init__(self, master, height=height, width=width, bg='#f0d9b5')
        self.network_client = network_client 
        self.step_record_chess_board = Record.Step_Record_Chess_Board()
        self.init_chess_board_points()    
        self.init_chess_board_canvas() 
        self.bind('<Button-1>', self.click_canvas)

    def init_chess_board_points(self):
        self.chess_board_points = [[None for i in range(15)] for j in range(15)]
        for i in range(15):
            for j in range(15):
                self.chess_board_points[i][j] = Point.Point(i, j)

    def init_chess_board_canvas(self):
        for i in range(15): 
            p1 = self.chess_board_points[i][0]
            p2 = self.chess_board_points[i][14]
            self.create_line(p1.pixel_x, p1.pixel_y, p2.pixel_x, p2.pixel_y)
        for j in range(15): 
            p1 = self.chess_board_points[0][j]
            p2 = self.chess_board_points[14][j]
            self.create_line(p1.pixel_x, p1.pixel_y, p2.pixel_x, p2.pixel_y)

    def click_canvas(self, event):
        i = round((event.x - 30) / 30)
        j = round((event.y - 30) / 30)
        
        if i < 0 or i > 14 or j < 0 or j > 14: return
        if self.step_record_chess_board.has_record(i, j): return
        self.draw_remote_move(i, j)
        frame = self.master.master 
        if hasattr(frame, 'network_client') and frame.network_client:
            msg = {"action": "game_move", "location": [i, j]}
            frame.network_client.send_msg(msg)
        else:
            self.after(500, self.ai_move)
            
    def execute_move(self, i, j):
        current_player = self.step_record_chess_board.who_to_play()
        color = 'white' if current_player == 1 else 'black'
        
        p = self.chess_board_points[i][j]
        self.create_oval(p.pixel_x-10, p.pixel_y-10, p.pixel_x+10, p.pixel_y+10, fill=color)
                         
        self.step_record_chess_board.insert_record(i, j)
        result = self.step_record_chess_board.check()
        if result == 1 or result == 2:
            winner = "White" if result == 1 else "Black"
            self.create_text(250, 480, text=f'{winner} Wins!', font=('Arial', 24, 'bold'), fill='red')
            self.unbind('<Button-1>')

    def draw_remote_move(self, i, j):
        if not self.step_record_chess_board.has_record(i, j):
            self.execute_move(i, j)
    
    def ai_move(self):
        if self.step_record_chess_board.check() in [1, 2]:
            return
        empty_spots = []
        for i in range(15):
            for j in range(15):
                if not self.step_record_chess_board.has_record(i, j):
                    empty_spots.append((i, j))
        if empty_spots:
            ai_i, ai_j = random.choice(empty_spots)
            self.draw_remote_move(ai_i, ai_j)


class Chess_Board_Frame(tkinter.Frame):
    def __init__(self, master=None, network_client=None):
        tkinter.Frame.__init__(self, master)
        self.network_client = network_client 
        self.create_widgets()

    def create_widgets(self):
        self.chess_board_label_frame = tkinter.LabelFrame(self, text="Gomoku Chat Mode", padx=5, pady=5)
        self.chess_board_label_frame.pack(padx=10, pady=10)
        self.chess_board_canvas = Chess_Board_Canvas(
            self.chess_board_label_frame, 
            height=500, width=500, 
            network_client=self.network_client
        )
        self.chess_board_canvas.pack()

