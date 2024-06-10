if __name__ == '__main__':
    from src.splash_screen import SplashScreen
    import multiprocessing as mp
    
    splash_screen_process = mp.Process(target=SplashScreen)
    splash_screen_process.start()

    from src.pipe_replacement_tool import PipeReplacementTool
    splash_screen_process.terminate()
    PipeReplacementTool()
    