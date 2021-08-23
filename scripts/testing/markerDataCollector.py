from __future__ import print_function
import os
import time, datetime 
from math import pi, atan2
import numpy as np
import pandas as pd
import cv2
import rospy
import tf, tf2_ros, tf_conversions
from sensor_msgs.msg import Image
from geometry_msgs.msg import TransformStamped, Pose
from cv_bridge import CvBridge
from flightgoggles.msg import IRMarkerArray
from scipy.spatial.transform import Rotation
from scipy.stats import truncnorm

class ImageMarkersDataSaver:
    def __init__(self, path):
        assert os.path.exists(path), 'provided path does not exit'
        self.path = path

        self.imageNamesList = []
        self.nameToImageDict = {}
        self.poseList = []
        self.markersArrayList = []
        self.samplesCount = 0
        self.dataSaved = False

    def addSample(self, imageName, image, markersArray, pose): 
        '''
            @param imageName: the name of the image to be saved.
            @param image: the corresponding image to be saved.
            @param markersArray: an np array of shape (4, 3), stores four rows each row contains (x, y, z). Where
                x, y are the location of the markers in the image, and z is the distace between the marker and the camera.
            @param pose: an np array of shape (7,). stores the pose of the drone when taking the image. the formate of the array is
                [x, y, z, qx, qy, qz, qw].
        '''
        assert markersArray.shape == (4, 3), 'markersArray shape does not equal to the expected one.'
        assert pose.shape == (7,), 'pose shape does not equal the expected one'

        self.imageNamesList.append(imageName)
        self.nameToImageDict[imageName] = image
        self.markersArrayList.append(markersArray)
        self.poseList.append(pose)
        self.samplesCount += 1
        return self.samplesCount
    
    def saveData(self):
        if self.dataSaved == False:
            print('saving data ...')
            self.dateID, self.imagesPath, self.dataPath = self.__createNewDirectory(self.path) 
            modifiedImageNameList = ['{}.jpg'.format(name) for name in self.imageNamesList]
            dataset = {
                'images': modifiedImageNameList,
                'markersArrays': self.markersArrayList,
                'poses': self.poseList
            }
            df = pd.DataFrame(dataset)
            df.to_pickle(os.path.join(self.dataPath, 'MarkersData_{}.pkl'.format(self.dateID) ) )
            for imageName in self.imageNamesList:
                image = self.nameToImageDict[imageName]
                cv2.imwrite(os.path.join(self.imagesPath, '{}.jpg'.format(imageName)), image)
                time.sleep(0.01)
            self.dataSaved = True
            return self.dateID

    def __createNewDirectory(self, base_path):
        dateId = datetime.datetime.today().strftime('%Y%m%d_%H%M%S')
        dir_name = 'ImageMarkersDataset_{}'.format(dateId)
        path = os.path.join(base_path, dir_name)
        os.makedirs(path)
        imagesPath = os.path.join(path, 'images')
        os.makedirs(imagesPath)
        dataPath = os.path.join(path, 'Markers_data')
        os.makedirs(dataPath)
        return dateId, imagesPath, dataPath

class ImageMarkersDataLoader:
    def __init__(self, basePath):
        self.imagesPath, self.markersDataPath = self.__processBasePath(basePath)

    def loadData(self):
        pickles = os.listdir(self.markersDataPath)
        # find the 'MarkerData' pickle file
        markerDataPickle = None
        for pickle in pickles:
            if pickle.startswith('MarkersData'):
                markerDataPickle = pickle
                break
        # read data   
        assert not markerDataPickle is None, 'could not find MarkersData pickle file'
        self.df = pd.read_pickle(os.path.join(self.markersDataPath, markerDataPickle))
        imageNamesList = self.df['images'].tolist()
        markersArrayList = self.df['markersArrays'].tolist()
        posesList = self.df['poses'].tolist()
        return imageNamesList, markersArrayList, posesList

    def loadImage(self, imageName):
        imageNameWithPath =  os.path.join(self.imagesPath, imageName)
        image = cv2.imread(imageNameWithPath)
        return image
    
    def getPathsDict(self):
        '''
            @return dictionary with keys: 'images', 'markersData'
        '''
        pathDict = {
            'Images': self.imagesPath,
            'MarkersData': self.markersDataPath
        }
        return pathDict

    def __processBasePath(self, basePath):
        imagesPath = os.path.join(basePath, 'images')
        markersDataPath = os.path.join(basePath, 'Markers_data')
        for path in [basePath, imagesPath, markersDataPath]:
            assert os.path.exists(path), 'path {} does not exist'.format(path)
        return imagesPath, markersDataPath

def testing_ImageMarkerDataSaver():
    path='/home/majd/catkin_ws/src/basic_rl_agent/data/test_imageMarkersData'
    imageMarkerSaver = ImageMarkersDataSaver(path)
    imageNameList = []
    markersArrayList = []
    posesList = []
    for i in range(10):
        image = np.random.randint(low=0, high=255, size=(224, 224, 3))
        imageName = 'image{}'.format(i)
        markersArray = np.random.rand(4, 3)
        pose = np.random.rand(7)

        # add data to list
        imageNameList.append('{}.jpg'.format(imageName))
        markersArrayList.append(markersArray)
        posesList.append(pose)
    
        imageMarkerSaver.addSample(imageName, image, markersArray, pose)

    dateID = imageMarkerSaver.saveData()

    path = os.path.join(path, 'ImageMarkersDataset_{}'.format(dateID))
    print('loading data from {}'.format(path))
    imageMarkerDataLoader = ImageMarkersDataLoader(path)
    loadedImageNameList, loadedMarkersArrayList, loadedPosesList = imageMarkerDataLoader.loadData()

    def compareTwoLists(l1, l2):
        sameLists = True 
        if len(l1) == len(l2):
            for i, v in enumerate(l1):
                if isinstance(v, np.ndarray):
                    if not (v == l2[i]).all():
                        sameLists = False
                        print(v, l2[i])
                        break
                else:
                    if v != l2[i]:
                        sameLists = False
                        print(v, l2[i])
                        break
        else:
            sameLists = False
            print('not the same length')
        assert sameLists, 'l1 and l2 are not the same'

    # compare:
    print('testing imageNameLists')
    compareTwoLists(imageNameList, loadedImageNameList)
    print('testing markersArrayLists')
    compareTwoLists(markersArrayList, loadedMarkersArrayList)
    print('testing posesLists')
    compareTwoLists(posesList, loadedPosesList)

    print('unitest passed for testing ImageMarkerDataSaver/Loader')

class ImageMarkersDataCollector:

    def __init__(self):
        rospy.init_node('image_markers_data_collector')

        self.bridge = CvBridge()
        self.transformListener = tf.TransformListener()
        # self.transformBroadcaster = tf2_ros.TransformBroadcaster()

        self.poseToBroadcast = [0, 0, 2, 0, 0, 0]
        self.firstImageMsgReceived = False
        cameraMatrix = np.array([548.4088134765625, 0.0, 512.0, 0.0, 548.4088134765625, 384.0, 0.0, 0.0, 1.0]).reshape(3, 3)
        self.fx, self.cx, self.fy, self.cy = cameraMatrix[0, 0], cameraMatrix[0, 2], cameraMatrix[1, 1], cameraMatrix[1, 2]
        self.FOV_Horizon = 42.3
        self.FOV_Vertical = 34.3
        self.gate6MarkersWorld = np.array([[-10.94867061,  -9.14866842, -9.14867044, -10.94867061],
                        [30.62329054, 30.6231606, 30.6231606, 30.62329054],
                        [1.97494068, 1.97494087, 3.82094047, 3.82094076]])
        self.gate6CenterWorld = np.array([-10.04867002, 30.62322557, 2.8979407]).reshape(3, 1)
        # saving data variables:
        self.imageMarkersSaverPath = '/home/majd/catkin_ws/src/basic_rl_agent/data/imageMarkersDataWithID' #imageMarkersData
        # self.imageMarkersSaver = None 
        self.processSample = False
        self.debug = False

        self.markerSubs = rospy.Subscriber('/uav/camera/left/ir_beacons', IRMarkerArray, self.irMarkerCallback, queue_size=1)
        self.CameraSubs = rospy.Subscriber('/uav/camera/left/image_rect_color', Image, self.cameraCallback, queue_size=1)
        self.posePub = rospy.Publisher('/uav/pose', Pose, queue_size=1)
        self.transformBroadcasterTimer = rospy.timer.Timer(rospy.Duration(0.1), self.timerCallback)

        print('image_markers_data_collector node initialized')
        time.sleep(0.5)
    
    def initImageMarkerDataSaver(self):
        self.imageMarkersSaver = ImageMarkersDataSaver(path=self.imageMarkersSaverPath)

    def irMarkerCallback(self, msg):
        self.lastIrMarkerArrayMsg = msg
        self.checkImageAndMarkers()
    
    def cameraCallback(self, msg):
        self.firstImageMsgReceived = True
        self.lastCameraMsg = msg
        self.checkImageAndMarkers()
    
    def checkImageAndMarkers(self):
        if not self.processSample:
            return 

        currCameraMsg = self.lastCameraMsg
        currMarkersMsg = self.lastIrMarkerArrayMsg

        # check if the two messages are syncronized
        imageTime = self.lastCameraMsg.header.stamp.to_sec()
        markersTime = self.lastIrMarkerArrayMsg.header.stamp.to_sec()
        if abs(imageTime - markersTime) != 0.0:
            print('msgs not synched')
            return

        # process the data.
        cv_image = self.bridge.imgmsg_to_cv2(self.lastCameraMsg, desired_encoding='bgr8')

        gatesMarkersDict = self.processMarkersMultiGate(currMarkersMsg)
        if 'Gate6' in gatesMarkersDict.keys():
            markersCoordinates = gatesMarkersDict['Gate6']
            if np.sum(markersCoordinates[:, -1] != 0, axis=0) < 3:
                print('2 or less of markers for Gate6 were found')
                self.processSample = False
                return None
        else:
            print('no markers for Gate6 were found')
            self.processSample = False
            return None

        if self.debug:
            for c in markersCoordinates:
                c = map(int, c)
                cv_image = cv2.circle(cv_image, (c[0], c[1]), radius=3, color=(0, 0, 255), thickness=-1)
        if len(markersCoordinates) < 4:
            for _ in range(4-len(markersCoordinates)):
                markersCoordinates.append((0, 0, 0))
        markersCoordinates = np.array(markersCoordinates)
        (trans,rot) = self.transformListener.lookupTransform('/world', '/uav/imu', rospy.Time(0))
        pose = np.array([trans + rot]).reshape(7,)
        assert np.allclose(pose, self.poseSent), 'the posed got from the lookup tranform is not close to the pose sent.'

        # @TODO change self.imageName
        self.imageName = 'im' + datetime.datetime.today().strftime('%Y%m%d_%H%M%S%f')[:-3]
        self.sampleCount = self.imageMarkersSaver.addSample(self.imageName, cv_image, markersCoordinates, pose)
        self.processSample = False

    def computeMarkers3DLocation(self):
        currCameraMsg = self.lastCameraMsg
        currMarkersMsg = self.lastIrMarkerArrayMsg

        # check if the two messages are syncronized
        imageTime = self.lastCameraMsg.header.stamp.to_sec()
        markersTime = self.lastIrMarkerArrayMsg.header.stamp.to_sec()
        if abs(imageTime - markersTime) != 0.0:
            print('msgs not synched')
            return None

        # process the data.
        cv_image = self.bridge.imgmsg_to_cv2(self.lastCameraMsg, desired_encoding='bgr8')

        gatesMarkersDict = self.processMarkersMultiGate(currMarkersMsg)
        if 'Gate6' in gatesMarkersDict.keys():
            markersCoordinates = gatesMarkersDict['Gate6']
        else:
            print('no markers for Gate6 were found')
            return None
        
        markersCoordinates = np.array(markersCoordinates)
        markers3DLocation = np.zeros_like(markersCoordinates)
        for i, marker in enumerate(markersCoordinates):
            x = (marker[0]-self.cx)*marker[2]/self.fx
            y = (marker[1]-self.cy)*marker[2]/self.fy
            markers3DLocation[i] = np.array([x, y, marker[2]])

        markers3DLocationCameraFrame = markers3DLocation.T
        markers3DLocationWorldFrame = self.transform(markers3DLocationCameraFrame, '/world', '/uav/camera/left')
        return markers3DLocationWorldFrame

    def pointDroneTowardsGate(self, mode='center'):
        if mode == 'center':
            gate6Center_droneFrame = self.transform(self.gate6CenterWorld, '/uav/imu', '/world')
            print(gate6Center_droneFrame)
            yawCorrection = atan2(gate6Center_droneFrame[1], gate6Center_droneFrame[0])
            yawCorrection = yawCorrection*180/pi
            currentYaw = self.poseToBroadcast[-1]
            yaw = currentYaw + yawCorrection
            print('yawCorrection', yawCorrection, 'yaw', yaw)
            self.poseToBroadcast[-1] = yaw
        elif mode.endswith('Yaw'):
            gate6Markers_droneFrame = self.transform(self.gate6MarkersWorld, '/uav/imu', '/world')
            YminMarkers = np.min(gate6Markers_droneFrame[1, :])
            YmaxMarkers = np.max(gate6Markers_droneFrame[1, :])
            X_yminMarker = gate6Markers_droneFrame[0, np.argmin(gate6Markers_droneFrame[1, :])]
            X_ymaxMarker = gate6Markers_droneFrame[0, np.argmax(gate6Markers_droneFrame[1, :])]
            if mode == 'maxYaw':
                print(YmaxMarkers, X_ymaxMarker)
                theta = atan2(YmaxMarkers, X_ymaxMarker)
                yawCorrection = theta*180/pi - self.FOV_Horizon
            elif mode == 'minYaw':
                print(YminMarkers, X_yminMarker)
                theta = atan2(YminMarkers, X_yminMarker)
                yawCorrection = theta*180/pi + self.FOV_Horizon
            currentYaw = self.poseToBroadcast[-1]
            yaw = currentYaw + yawCorrection
            print('yawCorrection', yawCorrection, 'yaw', yaw)
            self.poseToBroadcast[-1] = yaw
        elif mode.endswith('Pitch'):
            gate6Markers_droneFrame = self.transform(self.gate6MarkersWorld, '/uav/imu', '/world')
            ZminMarkers = np.min(gate6Markers_droneFrame[2, :])
            ZmaxMarkers = np.max(gate6Markers_droneFrame[2, :])
            X_zminMarker = gate6Markers_droneFrame[0, np.argmin(gate6Markers_droneFrame[2, :])]
            X_zmaxMarker = gate6Markers_droneFrame[0, np.argmax(gate6Markers_droneFrame[2, :])]
            if mode == 'maxPitch':
                print(ZmaxMarkers, X_zmaxMarker)
                angle = atan2(-ZmaxMarkers, X_zmaxMarker)
                pitchCorrection = angle*180/pi + self.FOV_Vertical
            elif mode == 'minPitch':
                print(ZminMarkers, X_zminMarker)
                angle = atan2(-ZminMarkers, X_zminMarker)
                pitchCorrection = angle*180/pi - self.FOV_Vertical
            currentPitch = self.poseToBroadcast[-2]
            pitch = currentPitch + pitchCorrection
            print('pitchCorrection', pitchCorrection, 'pitch', pitch)
            self.poseToBroadcast[-2] = pitch

    def computeYawPitchRanges(self):
        (trans,rot) = self.transformListener.lookupTransform('/world', '/uav/imu', rospy.Time(0))
        (currRoll, currPitch, currYaw) = tf.transformations.euler_from_quaternion(rot)
        currRoll, currPitch, currYaw = [angle*180/pi for angle in [currRoll, currPitch, currYaw]]
        # yaw and pitch center calculations:
        gate6Center_droneFrame = self.transform(self.gate6CenterWorld, '/uav/imu', '/world')
        yawCenter = atan2(gate6Center_droneFrame[1], gate6Center_droneFrame[0])*180/pi + currYaw
        pitchCenter = atan2(-gate6Center_droneFrame[2], gate6Center_droneFrame[0])*180/pi + currPitch
        # yaw and pitch min, max caclucations:
        gate6Markers_droneFrame = self.transform(self.gate6MarkersWorld, '/uav/imu', '/world')
        # yaw calculations:
        YminMarkers = np.min(gate6Markers_droneFrame[1, :])
        YmaxMarkers = np.max(gate6Markers_droneFrame[1, :])
        X_yminMarker = gate6Markers_droneFrame[0, np.argmin(gate6Markers_droneFrame[1, :])]
        X_ymaxMarker = gate6Markers_droneFrame[0, np.argmax(gate6Markers_droneFrame[1, :])]
        angle = atan2(YmaxMarkers, X_ymaxMarker)
        yawMax = angle*180/pi - self.FOV_Horizon + currYaw
        angle = atan2(YminMarkers, X_yminMarker)
        yawMin = angle*180/pi + self.FOV_Horizon + currYaw
        # pitch calculations:
        ZminMarkers = np.min(gate6Markers_droneFrame[2, :])
        ZmaxMarkers = np.max(gate6Markers_droneFrame[2, :])
        X_zminMarker = gate6Markers_droneFrame[0, np.argmin(gate6Markers_droneFrame[2, :])]
        X_zmaxMarker = gate6Markers_droneFrame[0, np.argmax(gate6Markers_droneFrame[2, :])]
        angle = atan2(-ZmaxMarkers, X_zmaxMarker)
        pitchMax = angle*180/pi + self.FOV_Vertical + currPitch
        angle = atan2(-ZminMarkers, X_zminMarker)
        pitchMin = angle*180/pi - self.FOV_Vertical + currPitch
        return [yawMin, yawCenter, yawMax, pitchMin, pitchCenter, pitchMax]

    def transform(self, Pc, toFrame, fromFrame):
        (trans,rot) = self.transformListener.lookupTransform(toFrame, fromFrame, rospy.Time(0))
        rotationMatrix = Rotation.from_quat(rot).as_dcm()
        trans = np.array(trans).reshape(3, 1)
        transformationMatrix = np.concatenate([rotationMatrix, trans], axis=1)
        transformationMatrix = np.vstack([transformationMatrix, np.array([0, 0, 0, 1]).reshape(1, 4)])
        Pc_homogeneous = np.vstack([Pc, np.ones((1, Pc.shape[1]))])
        Pw = np.matmul(transformationMatrix, Pc_homogeneous)
        return Pw[:-1, :] # remove the last row (all ones)

    def processMarkers(self, markersMsg):
        if len(markersMsg.markers) == 4:
            markersList = [0] * 4 
            for marker in markersMsg.markers:
                if marker.landmarkID.data == 'Gate6':
                    markerId = int(marker.markerID.data) - 1
                    markersList[markerId] = (marker.x, marker.y, marker.z)
                else:
                    print('a marker is not looking at Gate6')
                    return None
            return markersList
        else:
            print('the number of  markers is not 4.')
            return None

    def processMarkersMultiGate(self, markersMsg):
        gatesMarkersDict = {}
        for marker in markersMsg.markers:
            gate = marker.landmarkID.data
            if not gate in gatesMarkersDict.keys():
                gatesMarkersDict[gate] = np.zeros((4, 3))
            markerArray = gatesMarkersDict[gate]    
            markerId = int(marker.markerID.data)-1
            # markersList.append((marker.x, marker.y, marker.z))
            markerArray[markerId] = [marker.x, marker.y, marker.z]
        return gatesMarkersDict 

    # def timerCallback(self, msg):
    #     try:
    #         self.sendPose(self.poseToBroadcast[0], self.poseToBroadcast[1], self.poseToBroadcast[2], self.poseToBroadcast[3], self.poseToBroadcast[4], self.poseToBroadcast[5])
    #     except:
    #         pass

    def timerCallback(self, msg):
        self.sendPosePub(self.poseToBroadcast[0], self.poseToBroadcast[1], self.poseToBroadcast[2], self.poseToBroadcast[3], self.poseToBroadcast[4], self.poseToBroadcast[5])

    def sendPosePub(self, x, y, z, roll=0, pitch=0, yaw=0, q=None):
        msg = Pose()
        msg.position.x = x
        msg.position.y = y
        msg.position.z = z
        if q is None: 
            roll, pitch, yaw = [angle*pi/180.0 for angle in [roll, pitch, yaw]]
            q = tf_conversions.transformations.quaternion_from_euler(roll, pitch, yaw)
        msg.orientation.x = q[0]
        msg.orientation.y = q[1]
        msg.orientation.z = q[2]
        msg.orientation.w = q[3]
        self.posePub.publish(msg)
        self.poseSent = np.array([x, y, z, q[0], q[1], q[2], q[3]])

    def sendPose(self, x, y, z, roll=0, pitch=0, yaw=0, q=None):
        t = TransformStamped()
        t.header.stamp = rospy.Time.now()
        t.header.frame_id = "world"
        t.child_frame_id = "uav/imu"
        t.transform.translation.x = x
        t.transform.translation.y = y
        t.transform.translation.z = z
        if q is None: 
            roll, pitch, yaw = [angle*pi/180.0 for angle in [roll, pitch, yaw]]
            q = tf_conversions.transformations.quaternion_from_euler(roll, pitch, yaw)
        t.transform.rotation.x = q[0]
        t.transform.rotation.y = q[1]
        t.transform.rotation.z = q[2]
        t.transform.rotation.w = q[3]
        self.transformBroadcaster.sendTransform(t)
        self.poseSent = np.array([x, y, z, q[0], q[1], q[2], q[3]])

    def generateRandomPosition(self, gateX, gateY, gateZ):
        xmin, xmax = gateX - 3, gateX + 3
        ymin, ymax = gateY - 5, gateY - 18
        zmin, zmax = gateZ - 2.5, gateZ + 3
        x = xmin + np.random.rand() * (xmax - xmin)
        y = ymin + np.random.rand() * (ymax - ymin)
        z = zmin + np.random.rand() * (zmax - zmin)
        return x, y, z

    def generateRandomPoses(self, gateX, gateY, gateZ, size=1):
        roll_std = 3
        pitch_std = 8
        yaw_std = 25

        # generate random position (with random roll) and broadcast it:
        x, y, z = self.generateRandomPosition(gateX, gateY, gateZ)
        roll = 0 # np.random.normal(0, roll_std) # 68% is in range(0, roll_std), max, min roll is 5*segma degrees
        pitch, yaw = 0, 90
        self.poseToBroadcast = [x, y, z, roll, pitch, yaw]
        rospy.sleep(0.1)
        # compute yaw and pitch ranges 
        yawMin, yawCenter, yawMax, pitchMin, pitchCenter, pitchMax = self.computeYawPitchRanges()            
        # compute truncated normal rv parameters
        a_yaw, b_yaw = (yawMax-yawCenter)/yaw_std, (yawMin-yawCenter)/yaw_std
        a_pitch, b_pitch = (pitchMin-pitchCenter)/pitch_std, (pitchMax-pitchCenter)/pitch_std
        # randomPitchAngles = truncnorm.rvs(a_pitch, b_pitch, size=size) 
        # randomYawAngles = truncnorm.rvs(a_yaw, b_yaw, size=size)
        yawMin, yawMax = yawMax, yawMin
        randomPitchAngles = 0 #pitchMin + np.random.rand() * (pitchMax - pitchMin)
        randomYawAngles = yawMin + np.random.rand() * (yawMax-yawMin)
        randomPoses = [x, y, z, roll, randomPitchAngles, randomYawAngles]
        # randomPoses = []
        # for i in range(size):
        #     randomPoses = [x, y, z, roll, randomPitchAngles[i], randomYawAngles[i]]
        return randomPoses
 

    def run(self):
        gateX, gateY, gateZ = self.gate6CenterWorld.reshape(3, )
        # wait until fg opens
        while not self.firstImageMsgReceived:
            rospy.sleep(0.5)
        rospy.sleep(2)
    
        samplesNum = 1000
        epochs = 10
        for ep in range(epochs):
            print('epoch = {}'.format(ep))
            rate = rospy.Rate(4)
            self.sampleCount = 0
            self.initImageMarkerDataSaver()
            while not rospy.is_shutdown():
                randomPose = self.generateRandomPoses(gateX, gateY, gateZ) 
                self.poseToBroadcast = randomPose
                rospy.sleep(0.5)
                self.processSample = True
                while self.processSample:
                    rospy.sleep(0.1)
                rospy.sleep(0.1)
                print('epoch={}, sample={}'.format(ep, self.sampleCount))
                if self.sampleCount >= samplesNum:
                    self.imageMarkersSaver.saveData()
                    print('data saved.')
                    break
            if rospy.is_shutdown():
                break

    def rollPitchYaw_run(self):
        gateX, gateY, gateZ = -10.1, 30.65, 2.95
        # wait until fg opens
        while not self.firstImageMsgReceived:
            rospy.sleep(0.5)

        # x, y, z, roll, pitch, yaw = self.generateRandomPose(gateX, gateY, gateZ)
        x, y, z = (-10.422825041479353, 27, 1.67661692851683)
        roll, pitch, yaw = 0, 0, 90
        self.poseToBroadcast = [x, y, z, roll, pitch, yaw]
        rospy.sleep(2)
        rate = rospy.Rate(0.5)
        while not rospy.is_shutdown():
            x, y, z, roll, pitch, yaw = self.generateRandomPose(gateX, gateY, gateZ)
            self.poseToBroadcast = [x, y, z, roll, pitch, yaw]
            rospy.sleep(0.5)
            yawMin, yawCenter, yawMax, pitchMin, pitchCenter, pitchMax = self.computeYawPitchRanges()            
            self.poseToBroadcast[-2], self.poseToBroadcast[-1] = pitchCenter, yawCenter
            rospy.sleep(2)
            self.poseToBroadcast[-1] = yawMax
            rospy.sleep(2)
            self.poseToBroadcast[-1] = yawMin
            rospy.sleep(2)
            self.poseToBroadcast[-2], self.poseToBroadcast[-1] = pitchMax, yawCenter
            rospy.sleep(2)
            self.poseToBroadcast[-2] = pitchMin
            rospy.sleep(2)


def main():
    imageMarkersCollector = ImageMarkersDataCollector()
    imageMarkersCollector.run()
    # imageMarkersCollector.rollPitchYaw_run()
    

if __name__ == '__main__':
    main()