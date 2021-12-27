from multiprocessing import Process, Queue
import numpy
import time
import mss
import mss.tools
import os
import cv2


def screenshotter(args):
    queue = args[0]
    monitor = args[1]
    screenshotsPerSecond = args[2]
    
    localQueue = []
    screenshotsToTake = screenshotsPerSecond
    
    with mss.mss() as sct:
        now_ns = time.time_ns()
        endPeriod = now_ns + 1000000000

        while True:
            now_ns = time.time_ns()

            if screenshotsToTake:
                localQueue.append(( now_ns, sct.grab(monitor) ))
                screenshotsToTake -= 1

            # if the 1 second period is over
            if now_ns > endPeriod:
                queue.put(localQueue)
                localQueue = []
                endPeriod += 1000000000
                screenshotsToTake = screenshotsPerSecond


def writer(args):
    queue = args[0]
    splitQueue = args[1]

    outputFolder = "videosToSplit"
    fourcc = cv2.VideoWriter_fourcc(*'DIVX')
    localQueue = []
    filename = None
    buffered = []

    while True:
        for i in range(10):
            # localQueue is a 1s period
            localQueue = queue.get()

            (timestamp, img) = localQueue[0]
            localTime = time.localtime(timestamp / 1000000000)
            strTime = time.strftime("%X", localTime)
            ns = timestamp % 1000000000

            name = f"{strTime}.{ns:09d}"
            
            # Only open a new video file if it is the first iteration
            if not i:
                filename = f"{outputFolder}/{name}.avi"
                # It doesn't matter the frame specified, since we're 
                # not watching the video
                out = cv2.VideoWriter(filename, fourcc, 25, img.size)

            for (_, img) in localQueue:
                bgra = numpy.array(img)
                bgr = cv2.cvtColor(bgra, cv2.COLOR_BGRA2BGR)
                out.write(bgr)

            buffered.append((name, len(localQueue)))
            localQueue = []
        
        # Close the video file
        out.release()
        # Add the video to the queue to be splitted
        splitQueue.put((filename, buffered))
        filename = None
        buffered = []


def splitter(queue):
    while True:
        filename, buffer = queue.get()
        vidcap = cv2.VideoCapture(filename)
        success, image = vidcap.read()

        for (name, totalFrames) in buffer:
            frameNumber = 0

            while success and frameNumber < totalFrames:
                cv2.imwrite(f"screenshots/{name}#{frameNumber}.jpg", image)
                success, image = vidcap.read()
                frameNumber += 1

        os.remove(filename)


def main():
    print("Started. Press Ctrl+c to exit.")
    print("Note: The screenshots may take a few seconds to be written on disk, but they are being recorded.")

    # check for existence necessary directories 
    if not os.path.exists("videosToSplit"):
        os.makedirs("videosToSplit")
        print("Created folder videosToSplit to paste the raw material.")
    if not os.path.exists("screenshots"):
        os.makedirs("screenshots")
        print("Created folder screenshots to paste the images.")

    # queue for lists of screenshots. Each list contains screenshots 
    # of 1s period.
    queue = Queue()
    # queue of the generated videos to be splitted into the 
    # screenshot images
    splitQueue = Queue()
    # Limit of screenshots to take per second
    screenshotsPerSecond = 144
    # Adjust this to select the screen area to grab.
    # The smaller the area, the better the performance.
    # For a big area, the algorithm might not be able to keep up
    # with the chosen fps.
    region = {"top": 0, "left": 0, "width": 480, "height": 360}

    # processes
    ss1 = Process(target=screenshotter, args=((queue, region, screenshotsPerSecond),))
    writer1 = Process(target=writer, args=((queue, splitQueue),))
    writer2 = Process(target=writer, args=((queue, splitQueue),))
    splitter1 = Process(target=splitter, args=(splitQueue,))

    ss1.start()
    writer1.start()
    writer2.start()
    splitter1.start()
    
    try:
        ss1.join()
    except KeyboardInterrupt as e:
        print(e)

    ss1.terminate()
    writer1.terminate()
    writer2.terminate()
    splitter1.terminate()
    print("Exited successfully.")


if __name__ == "__main__":
    main()