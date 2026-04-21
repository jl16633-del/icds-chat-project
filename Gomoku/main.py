import GUI
import tkinter

if __name__ == '__main__':
    window = tkinter.Tk()
    gui_chess_board = GUI.Chess_Board_Frame(window)
    gui_chess_board.pack()
    window.mainloop()
