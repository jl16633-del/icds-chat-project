import tkinter
import math
import Point
import Record
import random

class Chess_Board_Canvas(tkinter.Canvas):
    def __init__(self, master=None, height=500, width=500, network_client=None, is_multiplayer=True):
        tkinter.Canvas.__init__(self, master, height=height, width=width, bg='#f0d9b5')
        self.network_client = network_client 
        self.is_multiplayer = is_multiplayer
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

        if self.is_multiplayer and hasattr(frame, 'network_client') and frame.network_client:
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
            self.create_text(250, 250, text=f'{winner} Wins!', font=('Arial', 36, 'bold'), fill='red')
            self.unbind('<Button-1>')

            if result == 1 and not self.is_multiplayer and self.network_client:
                self.network_client.send_msg({"action": "report_win"})

    def ai_move(self):
        if self.step_record_chess_board.check() in [1, 2]:
            return
            
        best_score = -1
        best_move = None

        for i in range(15):
            for j in range(15):
                if not self.step_record_chess_board.has_record(i, j):
                    score = self.evaluate_spot(i, j)
                    if score > best_score:
                        best_score = score
                        best_move = (i, j)
                        
        if best_move:
            self.draw_remote_move(best_move[0], best_move[1])

    def evaluate_spot(self, r, c):
        score = 0
        score += (7 - abs(7 - r)) + (7 - abs(7 - c))
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
        ai_color = self.step_record_chess_board.who_to_play()
        player_color = 1 if ai_color == 2 else 2

        for dr, dc in directions:

            ai_consecutive = self.count_consecutive(r, c, dr, dc, ai_color)
            player_consecutive = self.count_consecutive(r, c, dr, dc, player_color)
            score += 10 ** ai_consecutive
            score += (10 ** player_consecutive) * 1.2 
            
        return score

    def count_consecutive(self, r, c, dr, dc, color):
        count = 0
        for step in range(1, 5):
            nr, nc = r + dr*step, c + dc*step
            if 0 <= nr < 15 and 0 <= nc < 15:
                if self.step_record_chess_board.has_record(nr, nc) and self.step_record_chess_board.records[nr][nc].color == color:
                    count += 1
                else: break
            else: break
        for step in range(1, 5):
            nr, nc = r - dr*step, c - dc*step
            if 0 <= nr < 15 and 0 <= nc < 15:
                if self.step_record_chess_board.has_record(nr, nc) and self.step_record_chess_board.records[nr][nc].color == color:
                    count += 1
                else: break
            else: break
            
        return count

    def draw_remote_move(self, i, j):
        if not self.step_record_chess_board.has_record(i, j):
            self.execute_move(i, j)
    
class Chess_Board_Frame(tkinter.Frame):
    def __init__(self, master=None, network_client=None, is_multiplayer=True):
        tkinter.Frame.__init__(self, master)
        self.network_client = network_client 
        self.is_multiplayer = is_multiplayer
        self.create_widgets()

    def create_widgets(self):
        self.chess_board_label_frame = tkinter.LabelFrame(self, text="Gomoku Chat Mode", padx=5, pady=5)
        self.chess_board_label_frame.pack(padx=10, pady=10)
        self.chess_board_canvas = Chess_Board_Canvas(
            self.chess_board_label_frame, 
            height=500, width=500, 
            network_client=self.network_client,
            is_multiplayer=self.is_multiplayer
        )
        self.chess_board_canvas.pack()

