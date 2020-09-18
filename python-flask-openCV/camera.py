import cv2
import threading

class RecordingThread (threading.Thread):
    def __init__(self, name, camera):
        w     = 640         # largura do frame
        h     = 480         # altura do frame
        fps   = 20.0        # frames por segundo
        resolution = (w, h) # resolucao do frame

        threading.Thread.__init__(self)
        self.name = name
        self.isRunning = True

        self.cap = camera

        self.fourcc = cv2.VideoWriter_fourcc(*'H264')     # tambem pode ser usado (*'XVID')
        self.out = cv2.VideoWriter('./static/video.avi',self.fourcc, fps, (w, h), True)

        #fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        #self.out = cv2.VideoWriter('./static/video.avi',fourcc, 20.0, (640,480))      

    def run(self):
        while self.isRunning:
            ret, frame = self.cap.read()
            if ret:
                self.out.write(frame)
        self.out.release()

    def stop(self):
        self.isRunning = False

    def __del__(self):
        self.out.release()

class VideoCamera(object):
    def __init__(self):
        # Open a camera
        self.cap = cv2.VideoCapture(-1)
        if not self.cap.isOpened():
            raise RuntimeError('A camera nao pode ser iniciada!')
        # Initialize video recording environment
        self.is_record = False
        self.out = None

        # Thread for recording
        self.recordingThread = None
    
    def __del__(self):
        self.cap.release()
        print("A camera esta sendo desabilitada...")
    
    def get_frame(self):
        ret, frame = self.cap.read()

        if ret:
            ret, jpeg = cv2.imencode('.jpg', frame)
            return jpeg.tobytes()      
        else:
            return None

    def start_record(self):
        self.is_record = True
        self.recordingThread = RecordingThread("Gravacao de Video", self.cap)
        self.recordingThread.start()

    def stop_record(self):        
        self.is_record = False

        if self.recordingThread != None:
            self.recordingThread.stop()