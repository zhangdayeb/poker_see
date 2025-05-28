from cv2 import cv2
import numpy as np
import os,sys
import time
import json
import MySQLdb
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


from lib.read_poker_function_sys import *
from lib.read_poker_function_suanfa import *

# 此处 t_position = t1  p_position = l0 或者 r1 之类的
def change(t_positon,p_positon,game_type): 
    t1 = time.time()
    t_positon = str(t_positon)
    p_positon = str(p_positon)
    # 正常的处理的业务逻辑了    
    show('--------------------------------------------------------')
    show('图像处理：从原始小图 转向 二值的 花色 与 数字')
    show('--------------------------------------------------------')
    show("现在处理：")
    show("t_positon:"+str(t_positon))
    show("p_positon:"+str(p_positon))
    img_base_path_url = './temp_img/cut_photo/' + t_positon + '/p'+ p_positon
    cut_img_save_path_url = img_base_path_url + '/c_0.png'
    init_img = cv2.imread(cut_img_save_path_url) # 读取大图文件 生成 numpy 数组
    #################################################################################################
    #################################################################################################
    # 重要参数  start 
    #################################################################################################
    #################################################################################################
    # 扑克缩放
    poker_w = 855   # 扑克高度
    poker_h = 540   # 扑克宽度
    poker_light_level = 127 # 扑克花色跟数字 区分的 阈值设定
    #################################################################################################
    #################################################################################################
    # 重要参数  end 
    #################################################################################################
    #################################################################################################

    # 防止图片地址引用，导致数据变化 此处是因为不懂 怕相互影响的
    init_img_v1 = init_img.copy() # 第一步使用的，不影响下面
    init_img_v2 = init_img.copy() # 第二步使用的，变化后为 init_img_v3
    init_img_v3 = init_img.copy() # 第三步使用的，源头是第二步变化的

    ####################################################################################
    # 处理第一步：抠图 二值边框 灰度  ，找扑克牌，没有|太小 就返回
    ####################################################################################
    show('step1:    处理抠图，灰度，二值边框检测')
    gray = cv2.cvtColor(init_img_v1,cv2.COLOR_BGR2GRAY)# RGB 图像 转 灰度图像
    # 增加方差检测
    if (np.var(gray) < 1000):
        show('都是平板图像, 没有扑克')
        writeToMysql(t_positon,p_positon,{'rank':'0','suit':'0'},game_type)
        return '0|0'
    # 最小框图检测
    canny = cv2.Canny(gray,127,255) # 灰度 转 二值轮廓
    countours, hierarchys = cv2.findContours(canny,cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) # 二值边框数组 里面找到最大图，更容易
    areas = []  # 区域面积存储
    if len(countours) > 0: # 如果没有
        for c in range(len(countours)):
            areas.append(cv2.contourArea(countours[c]))
        max_id = areas.index(max(areas))    # 获取面积最大
        max_rect = cv2.minAreaRect(countours[max_id]) # 根据内容集，生成最小的贴合的，旋转的 矩形 得到最小外接矩形的（中心(x,y), (宽,高), 旋转角度） 这个是旋转的
        if max_rect[1][0] <60 or max_rect[1][1] < 60: # 防止 没有的 误判，有的会读取出来几个 , 判读一下，如果面积太小，肯定就不对了
            show("返回错误：面积太小 放弃")
            writeToMysql(t_positon,p_positon,{'rank':'0','suit':'0'},game_type)
            return '0|0'
    else:
        show("返回错误：没找到扑克 放弃")
        writeToMysql(t_positon,p_positon,{'rank':'0','suit':'0'},game_type)
        return '0|0'
    # 显示第一步的结果：
    cv2.imwrite(img_base_path_url + '/c_1.png', gray) # 显示灰度图片
    cv2.imwrite(img_base_path_url + '/c_2.png', canny) # 显示二值图片

    ####################################################################################
    # 处理第二步：旋转  横向的转成纵向的 纵向偏移的纠偏
    ####################################################################################
    show(max_rect)
    show('step2:    旋转 横向=>纵向 纵向=>调整角度')
    h , w = init_img_v2.shape[:2] # 用来判读 横向与纵向 
    if (init_img_v2.shape[0] < init_img_v2.shape[1]): 
        show('=横向=')
        center = (w / 2 , w / 2) # 神奇的错误，必须两个都是 w 才行哦，否则得到的不全.....................
        temp_h = 90
        if max_rect[2] < 10:
            temp_h = 90 + max_rect[2]
        else:
            temp_h = max_rect[2]
        M = cv2.getRotationMatrix2D(center, float(temp_h), 1)  # 移到这个位置，就是为了调整一下角度而已
        init_img_v3 = cv2.warpAffine(init_img_v2, M, (init_img_v2.shape[0],init_img_v2.shape[1]))
    else:
        show('纵向')
        center = (w / 2 , w / 2) # 神奇的错误，必须两个都是 w 才行哦，否则得到的不全.....................
        if max_rect[2] < 10.0:
            M = cv2.getRotationMatrix2D(center, max_rect[2], 1)  # 移到这个位置，就是为了调整一下角度而已  之前默认的 +1 现在修改为 +2 了
            init_img_v3 = cv2.warpAffine(init_img_v2, M, (init_img_v2.shape[1],init_img_v2.shape[0]))
    # 展示第二步的效果
    cv2.imwrite(img_base_path_url + '/c_3.png', init_img_v3)   # 显示标记图片

    ####################################################################################
    # 第三步：扑克去边 ， 整形
    ####################################################################################
    show('step3:    去边 最大化扑克：第一步标记扑克位置，第二步透视变换生成新图')
    gray = cv2.cvtColor(init_img_v3,cv2.COLOR_BGR2GRAY)#将图像转化为灰度图像
    canny = cv2.Canny(gray,127,255) # 二值轮廓图  
    # 代码优化一下 从边框图 变成 黑白二值图
    countours, hierarchys = cv2.findContours(canny,cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  
    areas = []  # 区域面积存储
    for c in range(len(countours)):
        areas.append(cv2.contourArea(countours[c]))
    max_id = areas.index(max(areas))    # 获取面积最大
    max_rect = cv2.minAreaRect(countours[max_id]) # 根据内容集，生成最小的贴合的，旋转的 矩形 得到最小外接矩形的（中心(x,y), (宽,高), 旋转角度）
    max_box = cv2.boxPoints(max_rect) # 获取最小外接矩形的4个顶点坐标(ps: cv2.boxPoints(rect) for OpenCV 3.x)  右下→左下→左上→右上
    max_box = np.int0(max_box) # 数据类型转换  float ==> int
    img2 = cv2.drawContours(init_img_v3,[max_box],0,(0,255,0),2) # 画框上来，方便看见，究竟如何了 就是为了 看看 寻找的对不对
    # 应对一个 横竖颠倒的数据 
    tmp_width = 0
    tmp_height = 0
    if max_rect[1][1] > max_rect[1][0]:
        tmp_width = max_rect[1][0]
        tmp_height = max_rect[1][1]
    else:
        tmp_width = max_rect[1][1]
        tmp_height = max_rect[1][0]


    # 整理应对的数组
    pts1 = np.float32(max_box) # pts1 原始位置记录  pts2 位置记录， 选择方向不一样，
    pts2 = np.float32([[max_rect[0][0]+tmp_width/2, max_rect[0][1]+tmp_height/2],
                    [max_rect[0][0]-tmp_width/2, max_rect[0][1]+tmp_height/2],
                    [max_rect[0][0]-tmp_width/2, max_rect[0][1]-tmp_height/2],
                    [max_rect[0][0]+tmp_width/2, max_rect[0][1]-tmp_height/2]])

    if(int(max_rect[2]) == 0):
        M = cv2.getPerspectiveTransform(pts1,pts1) # 0 度不变形
    else:
        M = cv2.getPerspectiveTransform(pts1,pts2) # 不是0度变形
    dst = cv2.warpPerspective(img2, M, (img2.shape[1],img2.shape[0])) # 参数说明： img2 变化原图像， M 变化的矩阵 img2.shape[1] img2.shape[0]  为变化后的尺寸，先列后行
    use_target = dst[int(pts2[2][1]):int(pts2[1][1]),int(pts2[2][0]):int(pts2[3][0])]# 生成比对的图片
    # 展示一下效果
    cv2.imwrite(img_base_path_url + '/c_4.png', dst)    # 显示 旋转后需要处理变形前的图片
    cv2.imwrite(img_base_path_url + '/c_5.png', img2)   # 显示扑克边框，方便人工判断
    cv2.imwrite(img_base_path_url + '/c_6.png', use_target)    # 显示 透视转换后的图片
    

    ####################################################################################
    # 第四步：切出来数字跟花色
    ####################################################################################
    show('step4:    取出扑克里面的花色跟数字')
    # 扑克牌缩放到指定尺寸
    poker_single_standard_size = (poker_h, poker_w) # 整理成变形的元祖数据
    poker_one_resized = cv2.resize(use_target, poker_single_standard_size, interpolation = cv2.INTER_AREA)
    cv2.imwrite(img_base_path_url + '/c_7.png', poker_one_resized)
    # 切图出来数字跟花色
    poker_rank_1 = poker_one_resized[30:140, 25:85]  # 裁剪坐标为[y0:y1, x0:x1] 数字大小 70 * 125
    cv2.imwrite(img_base_path_url + '/c_8.png', poker_rank_1)
    poker_suit_1 = poker_one_resized[140:225, 25:85] # 花色大小 70 * 100
    cv2.imwrite(img_base_path_url + '/c_9.png', poker_suit_1)
    # 对花色跟数字图片再次变形处理，方便后期二值比对
    poker_rank = cv2.resize(poker_rank_1, (70,125), interpolation = cv2.INTER_AREA)
    poker_suit = cv2.resize(poker_suit_1, (70,100), interpolation = cv2.INTER_AREA)
    # 获取灰度图片
    poker_rank_gray = cv2.cvtColor(poker_rank,cv2.COLOR_BGR2GRAY)
    poker_suit_gray = cv2.cvtColor(poker_suit,cv2.COLOR_BGR2GRAY)
    # 增加个边框检测，看看效果能不能更好一点
    poker_rank_canny = cv2.Canny(poker_rank_gray,127,255) # 灰度 转 二值轮廓
    poker_suit_canny = cv2.Canny(poker_suit_gray,127,255) # 灰度 转 二值轮廓
    # 对灰度图片进行二值化  方便后面去找边界 怎么感觉像是取反呢？
    #################################################################################################
    #################################################################################################
    # 重要参数 ############### 超级重要参数的修改，根据灯光不同，可能需要修改不一样的阈值 190 目前是最好的
    #################################################################################################
    #################################################################################################
    _,poker_rank_thresh = cv2.threshold(poker_rank_gray,poker_light_level,255,cv2.THRESH_BINARY_INV)
    _,poker_suit_thresh = cv2.threshold(poker_suit_gray,poker_light_level,255,cv2.THRESH_BINARY_INV)
    # 存储转换完成的二值话的图形 存储边框二值
    # uu = uuid.uuid4().hex
    uu = 'x'
    file_name1 = img_base_path_url + '/c_10.png'
    file_name2 = img_base_path_url + '/c_11.png'
    file_name5 = img_base_path_url + '/c_12.png'
    file_name6 = img_base_path_url + '/c_13.png'
    cv2.imwrite(file_name1, poker_rank_canny)
    cv2.imwrite(file_name2, poker_suit_canny)
    cv2.imwrite(file_name5, poker_rank_thresh)
    cv2.imwrite(file_name6, poker_suit_thresh)
    # 二值化的对比图，重新裁剪里面最大的图像出来，然后进行对比
    # 此处有个 bug
    contours_last_rank, hierarchy = cv2.findContours(poker_rank_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    areas_last_rank = []  # 区域面积存储
    if len(contours_last_rank) > 0:
        for c in range(len(contours_last_rank)):
            areas_last_rank.append(cv2.contourArea(contours_last_rank[c]))
        max_id_last_rank = areas_last_rank.index(max(areas_last_rank))    # 获取面积最大
        [t_x , t_y, t_w, t_h] = cv2.boundingRect(contours_last_rank[max_id_last_rank])
        poker_rank_thresh_full = poker_rank_thresh[t_y:t_y+t_h,t_x:t_x+t_w]
        poker_rank_thresh_full = cv2.resize(poker_rank_thresh_full, (70,125), interpolation = cv2.INTER_AREA)
        # 存放数字全屏最大的图片
        file_name3 = img_base_path_url + '/c_14.png'
        cv2.imwrite(file_name3, poker_rank_thresh_full)
    else:
        show('返回错误：没找到数字 ')
        writeToMysql(t_positon,p_positon,{'rank':'0','suit':'0'},game_type)
        return '0|0'
    # 花色缩放
    contours_last_suit, hierarchy = cv2.findContours(poker_suit_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    areas_last_suit = []  # 区域面积存储
    if len(contours_last_suit) > 0:
        for c in range(len(contours_last_suit)):
            areas_last_suit.append(cv2.contourArea(contours_last_suit[c]))
        max_id_last_suit = areas_last_suit.index(max(areas_last_suit))    # 获取面积最大
        if len(contours_last_suit) > 0:
            [t_x , t_y, t_w, t_h] = cv2.boundingRect(contours_last_suit[max_id_last_suit])
        else:
            [t_x , t_y, t_w, t_h] = [0,0,1,1]
        poker_suit_thresh_full = poker_suit_thresh[t_y:t_y+t_h,t_x:t_x+t_w]
        poker_suit_thresh_full = cv2.resize(poker_suit_thresh_full, (70,100), interpolation = cv2.INTER_AREA)
        # 存放花色全屏最大的图片
        file_name4 = img_base_path_url + '/c_15.png'
        cv2.imwrite(file_name4, poker_suit_thresh_full)
    else:
        show('返回错误：没找到花色 ')
        writeToMysql(t_positon,p_positon,{'rank':'0','suit':'0'},game_type)
        return '0|0'


    ####################################################################################
    # 第五步：处理完成，进行算法比对，最主要的是防止 误判
    ####################################################################################
    img_base_path_url = './temp_img/cut_photo/' + t_positon + '/p'+ p_positon
    cut_img_save_path_url_rank = img_base_path_url + '/c_14.png'
    cut_img_save_path_url_suit= img_base_path_url + '/c_15.png'
    train_ranks = load_ranks("./know_img/lib/Card_Imgs/")
    train_suits = load_suits("./know_img/lib/Card_Imgs/")
    img_v1 = cv2.imread(cut_img_save_path_url_rank)
    img_v2 = cv2.imread(cut_img_save_path_url_suit)
    rank_text = get_rank_and_suit_v3(train_ranks,img_v1,'r') # r 代表数字
    suit_text = get_rank_and_suit_v3(train_suits,img_v2,'s') # s 代表花色

    show(rank_text)
    show(suit_text)
    data = {'rank':rank_text,'suit':suit_text}
    # 数据库存储
    writeToMysql(t_positon,p_positon,data,game_type)
    # 如果没有数据 
    # writeToMysql(t_positon,p_positon,{'rank':'0','suit':'0'},game_type)
    # 干活结束
    t2 = time.time()
    show("拆解图片 时间:")
    show(t2 - t1) 



def writeToMysql(t_positon,p_positon,data,game_type):
    p_positon = str(p_positon)
    data_str = json.dumps(data)
    sql = 'UPDATE `tu_'+game_type+'_result` SET `result` = \''+data_str+'\' WHERE `position` = \''+t_positon+'_p'+p_positon+'\''
    show_trace("成功获取到信息："+sql)
    # 打开数据库连接
    db = MySQLdb.connect("127.0.0.1", "root", "root", "tuxiang", charset='utf8' )
    # 使用cursor()方法获取操作游标 
    cursor = db.cursor()
    # 使用execute方法执行SQL语句
    cursor.execute(sql)
    # 使用 fetchone() 方法获取一条数据
    data = cursor.fetchone()
    # 关闭数据库连接
    db.close()


