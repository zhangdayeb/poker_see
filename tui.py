#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时识别推送系统 - tui.py (数据库版本)
业务逻辑:
1. 读取摄像头配置
2. 轮询拍照
3. 轮询裁剪
4. 轮询混合识别 (YOLO + OCR + OpenCV)
5. 结果合并优化
6. 写入远程数据库
"""

import sys
import time
import json
import signal
import argparse
import threading
import pymysql
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# 路径设置
def setup_project_paths():
    """设置项目路径"""
    current_file = Path(__file__).resolve()
    project_root = current_file.parent
    
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    return project_root

PROJECT_ROOT = setup_project_paths()

class DatabaseTuiSystem:
    """数据库版实时识别推送系统"""
    
    def __init__(self):
        """初始化系统"""
        self.shutdown_requested = False
        
        # 系统配置
        self.config = {
            'recognition_interval': 3,  # 每轮循环间隔(秒)
            'camera_switch_delay': 1,   # 摄像头切换延迟(秒)
            'max_retry_times': 3,       # 最大重试次数
            'retry_delay': 2,           # 重试延迟(秒)
            'enable_database': True,    # 启用数据库写入
            'save_recognition_results': True,  # 保存识别结果
            'enable_result_merging': True,  # 启用结果合并
        }
        
        # 数据库配置
        self.db_config = {
            'host': '134.122.197.44',
            'user': 'tuxiang',
            'password': 'JjEAhCEArRAHYcD8',
            'database': 'tuxiang',
            'port': 3306,
            'charset': 'utf8',
            'connect_timeout': 10,
            'read_timeout': 10,
            'write_timeout': 10,
            'autocommit': True
        }
        
        # 混合识别器配置
        self.recognition_config = {
            # YOLO配置
            'yolo_enabled': True,
            'yolo_confidence_threshold': 0.3,
            'yolo_high_confidence_threshold': 0.8,
            
            # OCR配置
            'ocr_enabled': True,
            'ocr_confidence_threshold': 0.3,
            'ocr_prefer_paddle': True,
            
            # OpenCV花色识别配置
            'opencv_suit_enabled': True,
            'opencv_suit_confidence_threshold': 0.4,
            
            # 融合策略配置
            'fusion_strategy': 'weighted',  # weighted, voting, priority
            'min_confidence_for_result': 0.3,
            'enable_result_validation': True,
            
            # 性能配置
            'debug_mode': False,
            'save_intermediate_results': False
        }
        
        # 结果合并器配置
        self.merger_config = {
            'min_confidence_threshold': 0.3,
            'high_confidence_threshold': 0.8,
            'conflict_resolution_strategy': 'highest_confidence',
            'enable_consistency_check': True,
            'quality_assessment_enabled': True,
            'duplicate_detection_enabled': True,
            'include_metadata': True,
            'include_quality_metrics': True
        }
        
        # 位置映射配置
        self.position_mapping = {
            'zhuang_1': 't1_pl0',
            'zhuang_2': 't1_pl1',
            'zhuang_3': 't1_pl2',
            'xian_1': 't1_pr0',
            'xian_2': 't1_pr1',
            'xian_3': 't1_pr2'
        }
        
        # 点数转换映射
        self.rank_mapping = {
            '': 0, 'A': 1, '2': 2, '3': 3, '4': 4, '5': 5,
            '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
            'J': 11, 'Q': 12, 'K': 13
        }
        
        # 花色转换映射
        self.suit_mapping = {
            '': '0',
            'hearts': 'r',    # 红桃
            'diamonds': 'f',  # 方块
            'clubs': 'm',     # 梅花
            'spades': 'h'     # 黑桃
        }
        
        # 摄像头配置
        self.enabled_cameras = []
        self.current_camera_index = 0
        
        # 数据库连接池
        self.db_connection = None
        
        # 统计信息
        self.stats = {
            'start_time': datetime.now(),
            'total_cycles': 0,
            'camera_stats': {},
            'last_results': {},
            'database_stats': {
                'total_writes': 0,
                'successful_writes': 0,
                'failed_writes': 0,
                'total_initializations': 0,
                'successful_initializations': 0,
                'last_write_time': None,
                'connection_errors': 0
            },
            'recognition_method_stats': {
                'yolo_complete': 0,
                'hybrid_combined': 0,
                'ocr_only': 0,
                'opencv_only': 0,
                'failed': 0
            },
            'quality_stats': {
                'excellent': 0,
                'good': 0,
                'average': 0,
                'poor': 0,
                'very_poor': 0
            }
        }
        
        # 显示状态
        self.display_lock = threading.Lock()
        
        print("🚀 数据库版实时识别推送系统初始化完成")
    
    def _init_database_connection(self) -> bool:
        """初始化数据库连接"""
        try:
            print("\n🗄️  初始化数据库连接...")
            print(f"   服务器: {self.db_config['host']}:{self.db_config['port']}")
            print(f"   数据库: {self.db_config['database']}")
            print(f"   用户: {self.db_config['user']}")
            
            self.db_connection = pymysql.connect(**self.db_config)
            
            # 测试连接
            with self.db_connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM tu_bjl_result")
                count = cursor.fetchone()[0]
                print(f"✅ 数据库连接成功，表中有 {count} 条记录")
            
            return True
            
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            self.stats['database_stats']['connection_errors'] += 1
            return False
    
    def _ensure_database_connection(self) -> bool:
        """确保数据库连接有效"""
        try:
            if self.db_connection is None:
                return self._init_database_connection()
            
            # 测试连接是否有效
            self.db_connection.ping(reconnect=True)
            return True
            
        except Exception as e:
            print(f"⚠️  数据库连接断开，尝试重连: {e}")
            self.stats['database_stats']['connection_errors'] += 1
            return self._init_database_connection()
    
    def _get_table_id_from_config(self, camera_id: str) -> int:
        """从配置文件获取tableId"""
        try:
            # 从启用的摄像头中查找
            for camera in self.enabled_cameras:
                if camera.get('id') == camera_id:
                    table_id = camera.get('tableId', 1)  # 默认值为1
                    return table_id
            
            # 如果没找到，返回默认值
            print(f"⚠️  未找到摄像头 {camera_id} 的tableId配置，使用默认值1")
            return 1
            
        except Exception as e:
            print(f"❌ 获取tableId失败: {e}")
            return 1
    
    def _camera_data_exists(self, camera_id: str, table_id: int) -> bool:
        """检查摄像头数据是否存在"""
        try:
            with self.db_connection.cursor() as cursor:
                sql = "SELECT COUNT(*) FROM tu_bjl_result WHERE camera_id = %s AND tableId = %s"
                cursor.execute(sql, (camera_id, table_id))
                count = cursor.fetchone()[0]
                return count > 0
                
        except Exception as e:
            print(f"❌ 检查摄像头数据存在性失败: {e}")
            return False
    
    def _insert_initial_camera_data(self, camera_id: str, table_id: int) -> bool:
        """插入摄像头的初始6条记录"""
        try:
            print(f"      🔧 初始化摄像头 {camera_id} 数据 (tableId: {table_id})")
            
            # 准备6条初始记录
            initial_records = []
            for position in ['t1_pl0', 't1_pl1', 't1_pl2', 't1_pr0', 't1_pr1', 't1_pr2']:
                initial_records.append((
                    position,
                    '{"rank": "0", "suit": "0"}',
                    camera_id,
                    table_id
                ))
            
            with self.db_connection.cursor() as cursor:
                sql = "INSERT INTO tu_bjl_result (position, result, camera_id, tableId) VALUES (%s, %s, %s, %s)"
                cursor.executemany(sql, initial_records)
            
            # 提交事务
            self.db_connection.commit()
            
            # 更新统计
            self.stats['database_stats']['total_initializations'] += 1
            self.stats['database_stats']['successful_initializations'] += 1
            
            print(f"      ✅ 成功初始化 {len(initial_records)} 条记录")
            return True
            
        except Exception as e:
            # 回滚事务
            if self.db_connection:
                self.db_connection.rollback()
            
            print(f"      ❌ 初始化摄像头数据失败: {e}")
            self.stats['database_stats']['total_initializations'] += 1
            return False
    
    def _update_camera_results(self, camera_id: str, table_id: int, formatted_results: Dict[str, Any]) -> Dict[str, Any]:
        """更新摄像头识别结果"""
        try:
            positions = formatted_results.get('positions', {})
            updated_count = 0
            
            with self.db_connection.cursor() as cursor:
                for system_position, result_data in positions.items():
                    if system_position in self.position_mapping:
                        db_position = self.position_mapping[system_position]
                        
                        # 转换数据格式
                        rank_value = self.rank_mapping.get(result_data.get('rank', ''), 0)
                        suit_value = self.suit_mapping.get(result_data.get('suit', ''), '0')
                        
                        # 构建JSON字符串
                        result_json = json.dumps({
                            "rank": str(rank_value),
                            "suit": suit_value
                        })
                        
                        # 执行更新，增加tableId条件
                        sql = "UPDATE tu_bjl_result SET result = %s WHERE camera_id = %s AND tableId = %s AND position = %s"
                        cursor.execute(sql, (result_json, camera_id, table_id, db_position))
                        
                        if cursor.rowcount > 0:
                            updated_count += 1
            
            # 提交事务
            self.db_connection.commit()
            
            return {
                'success': True,
                'message': f'成功更新 {updated_count} 条记录',
                'updated_count': updated_count
            }
            
        except Exception as e:
            # 回滚事务
            if self.db_connection:
                self.db_connection.rollback()
            
            return {
                'success': False,
                'message': f'数据库更新失败: {str(e)}',
                'updated_count': 0
            }
    
    def step1_load_camera_config(self) -> bool:
        """步骤1: 读取摄像头配置"""
        try:
            print("\n📷 步骤1: 读取摄像头配置")
            print("-" * 50)
            
            # 使用配置管理器
            from src.core.config_manager import get_all_cameras
            
            result = get_all_cameras()
            if result['status'] != 'success':
                print(f"❌ 获取摄像头配置失败: {result['message']}")
                return False
            
            cameras = result['data']['cameras']
            if not cameras:
                print("❌ 没有找到摄像头配置")
                return False
            
            # 过滤启用的摄像头
            self.enabled_cameras = [c for c in cameras if c.get('enabled', True)]
            if not self.enabled_cameras:
                print("❌ 没有找到启用的摄像头")
                return False
            
            print(f"✅ 找到 {len(self.enabled_cameras)} 个启用的摄像头:")
            for i, camera in enumerate(self.enabled_cameras):
                camera_id = camera['id']
                table_id = camera.get('tableId', 1)
                
                # 初始化摄像头统计
                self.stats['camera_stats'][camera_id] = {
                    'total_attempts': 0,
                    'successful_photos': 0,
                    'successful_recognitions': 0,
                    'successful_writes': 0,
                    'data_initialized': False,
                    'last_photo_time': None,
                    'last_recognition_time': None,
                    'last_write_time': None,
                    'last_result': None,
                    'table_id': table_id,
                    'recognition_method_counts': {
                        'yolo_complete': 0,
                        'hybrid_combined': 0,
                        'ocr_only': 0,
                        'opencv_only': 0
                    },
                    'average_quality_score': 0.0,
                    'quality_history': []
                }
                
                print(f"   {i+1}. {camera['name']} (ID: {camera_id}, tableId: {table_id}) - IP: {camera['ip']}")
            
            return True
            
        except Exception as e:
            print(f"❌ 读取摄像头配置失败: {e}")
            return False
    
    def step2_take_photo(self, camera_id: str) -> Dict[str, Any]:
        """步骤2: 拍照"""
        try:
            # 导入拍照控制器
            from src.processors.photo_controller import take_photo_by_id
            
            start_time = time.time()
            result = take_photo_by_id(camera_id)
            duration = time.time() - start_time
            
            # 更新统计
            self.stats['camera_stats'][camera_id]['total_attempts'] += 1
            
            if result['status'] == 'success':
                self.stats['camera_stats'][camera_id]['successful_photos'] += 1
                self.stats['camera_stats'][camera_id]['last_photo_time'] = datetime.now().strftime('%H:%M:%S')
                
                return {
                    'success': True,
                    'file_path': result['data']['file_path'],
                    'filename': result['data']['filename'],
                    'file_size': result['data']['file_size'],
                    'duration': duration
                }
            else:
                return {
                    'success': False,
                    'error': result['message'],
                    'duration': duration
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'duration': 0
            }
    
    def step3_crop_images(self, image_path: str) -> Dict[str, Any]:
        """步骤3: 裁剪图片"""
        try:
            from src.processors.image_cutter import process_image
            
            start_time = time.time()
            success = process_image(image_path)
            duration = time.time() - start_time
            
            if success:
                # 查找裁剪后的图片
                image_file = Path(image_path)
                cut_dir = image_file.parent / "cut"
                
                if cut_dir.exists():
                    pattern = f"{image_file.stem}_*.png"
                    all_files = list(cut_dir.glob(pattern))
                    
                    # 分离主图片和左上角图片
                    main_files = [f for f in all_files if not f.name.endswith('_left.png')]
                    left_files = [f for f in all_files if f.name.endswith('_left.png')]
                    
                    main_files.sort(key=lambda x: x.name)
                    left_files.sort(key=lambda x: x.name)
                    
                    return {
                        'success': True,
                        'main_files': [str(f) for f in main_files],
                        'left_files': [str(f) for f in left_files],
                        'total_count': len(main_files),
                        'duration': duration
                    }
                else:
                    return {
                        'success': False,
                        'error': '裁剪目录不存在',
                        'duration': duration
                    }
            else:
                return {
                    'success': False,
                    'error': '图片裁剪失败',
                    'duration': duration
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'duration': 0
            }
    
    def step4_recognize_images_hybrid(self, camera_id: str, main_files: List[str], left_files: List[str]) -> Dict[str, Any]:
        """步骤4: 混合识别扑克牌"""
        try:
            from src.processors.poker_hybrid_recognizer import recognize_poker_card_hybrid
            
            position_results = {}
            successful_count = 0
            total_count = len(main_files)
            
            # 创建主图片和左上角图片的对应关系
            main_to_left_map = self._create_image_mapping(main_files, left_files)
            
            start_time = time.time()
            
            for i, main_image_path in enumerate(main_files):
                position = self._extract_position_from_filename(Path(main_image_path).name)
                left_image_path = main_to_left_map.get(main_image_path)
                
                # 使用混合识别器
                result = recognize_poker_card_hybrid(
                    main_image_path, 
                    left_image_path,
                    config=self.recognition_config
                )
                
                if result['success']:
                    successful_count += 1
                    
                    # 统计识别方法
                    self._update_recognition_method_stats(camera_id, result)
                
                position_results[position] = result
            
            duration = time.time() - start_time
            
            # 更新统计
            if successful_count > 0:
                self.stats['camera_stats'][camera_id]['successful_recognitions'] += 1
                self.stats['camera_stats'][camera_id]['last_recognition_time'] = datetime.now().strftime('%H:%M:%S')
            
            return {
                'success': successful_count > 0,
                'position_results': position_results,
                'successful_count': successful_count,
                'total_count': total_count,
                'success_rate': (successful_count / total_count * 100) if total_count > 0 else 0,
                'duration': duration
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'duration': 0
            }
    
    def step5_merge_results(self, camera_id: str, position_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """步骤5: 合并和优化识别结果"""
        try:
            if not self.config['enable_result_merging']:
                # 如果禁用合并，直接格式化结果
                return self._format_recognition_results_simple(camera_id, position_results)
            
            from src.processors.poker_result_merger import merge_poker_recognition_results
            
            metadata = {
                'system_mode': 'realtime_database',
                'fusion_strategy': self.recognition_config['fusion_strategy'],
                'timestamp': datetime.now().isoformat()
            }
            
            start_time = time.time()
            merge_result = merge_poker_recognition_results(
                position_results,
                camera_id=camera_id,
                metadata=metadata,
                config=self.merger_config
            )
            duration = time.time() - start_time
            
            # 更新质量统计
            if merge_result.get('success') and 'quality' in merge_result:
                self._update_quality_stats(camera_id, merge_result['quality'])
            
            # 转换为数据库格式
            if merge_result.get('success'):
                formatted_result = self._convert_merge_result_to_database_format(camera_id, merge_result)
                formatted_result['merge_duration'] = duration
                return formatted_result
            else:
                return {
                    'success': False,
                    'error': merge_result.get('error', '结果合并失败'),
                    'duration': duration
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'duration': 0
            }
    
    def step6_write_to_database(self, camera_id: str, formatted_results: Dict[str, Any]) -> Dict[str, Any]:
        """步骤6: 写入远程数据库"""
        try:
            if not self.config['enable_database']:
                return {'success': True, 'message': '数据库写入已禁用', 'duration': 0}
            
            start_time = time.time()
            
            # 确保数据库连接有效
            if not self._ensure_database_connection():
                return {
                    'success': False,
                    'message': '数据库连接失败',
                    'duration': time.time() - start_time
                }
            
            # 1. 从配置获取tableId
            table_id = self._get_table_id_from_config(camera_id)
            
            # 2. 检查摄像头数据是否存在
            if not self._camera_data_exists(camera_id, table_id):
                # 3. 不存在则插入6条初始记录
                if not self._insert_initial_camera_data(camera_id, table_id):
                    return {
                        'success': False,
                        'message': '初始化摄像头数据失败',
                        'duration': time.time() - start_time
                    }
                # 标记数据已初始化
                self.stats['camera_stats'][camera_id]['data_initialized'] = True
            
            # 显示识别结果
            self._display_recognition_results_table(formatted_results, table_id)
            
            # 4. 更新识别结果
            write_result = self._update_camera_results(camera_id, table_id, formatted_results)
            
            duration = time.time() - start_time
            
            # 更新统计
            self.stats['database_stats']['total_writes'] += 1
            if write_result['success']:
                self.stats['database_stats']['successful_writes'] += 1
                self.stats['database_stats']['last_write_time'] = datetime.now().strftime('%H:%M:%S')
                self.stats['camera_stats'][camera_id]['successful_writes'] += 1
                self.stats['camera_stats'][camera_id]['last_write_time'] = datetime.now().strftime('%H:%M:%S')
            else:
                self.stats['database_stats']['failed_writes'] += 1
            
            return {
                'success': write_result['success'],
                'message': write_result['message'],
                'duration': duration,
                'updated_count': write_result.get('updated_count', 0)
            }
            
        except Exception as e:
            self.stats['database_stats']['failed_writes'] += 1
            return {
                'success': False,
                'message': str(e),
                'duration': 0
            }
    
    def _display_recognition_results_table(self, formatted_results: Dict[str, Any], table_id: int):
        """以表格形式显示识别结果"""
        with self.display_lock:
            positions = formatted_results.get('positions', {})
            camera_id = formatted_results.get('camera_id', '')
            
            print(f"      📊 识别结果展示 (camera_id: {camera_id}, tableId: {table_id}):")
            print("      ┌─────────┬─────────┬────────┬─────────┬──────────┐")
            print("      │ 位置    │ 系统结果│ 数据库位置│ 转换结果│ 置信度   │")
            print("      ├─────────┼─────────┼────────┼─────────┼──────────┤")
            
            position_names = {
                'zhuang_1': '庄1', 'zhuang_2': '庄2', 'zhuang_3': '庄3',
                'xian_1': '闲1', 'xian_2': '闲2', 'xian_3': '闲3'
            }
            
            for position in ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']:
                result_data = positions.get(position, {})
                
                # 系统结果
                suit = result_data.get('suit', '')
                rank = result_data.get('rank', '')
                confidence = result_data.get('confidence', 0.0)
                
                if suit and rank:
                    suit_symbol = {'hearts': '♥️', 'diamonds': '♦️', 'clubs': '♣️', 'spades': '♠️'}.get(suit, '')
                    system_result = f"{suit_symbol}{rank}"
                else:
                    system_result = "未识别"
                
                # 转换结果
                rank_value = self.rank_mapping.get(rank, 0)
                suit_value = self.suit_mapping.get(suit, '0')
                converted_result = f"{suit_value},{rank_value}"
                
                # 数据库位置
                db_position = self.position_mapping.get(position, '')
                
                # 格式化显示
                pos_name = position_names.get(position, position)
                confidence_str = f"{confidence*100:.1f}%" if confidence > 0 else "0.0%"
                
                print(f"      │ {pos_name:<7} │ {system_result:<7} │ {db_position:<6} │ {converted_result:<7} │ {confidence_str:<8} │")
            
            print("      └─────────┴─────────┴────────┴─────────┴──────────┘")
    
    def _create_image_mapping(self, main_files: List[str], left_files: List[str]) -> Dict[str, str]:
        """创建主图片和左上角图片的对应关系"""
        mapping = {}
        
        for main_file in main_files:
            main_stem = Path(main_file).stem  # camera_001_zhuang_1
            
            # 查找对应的左上角图片
            for left_file in left_files:
                left_stem = Path(left_file).stem  # camera_001_zhuang_1_left
                if left_stem.startswith(main_stem):
                    mapping[main_file] = left_file
                    break
        
        return mapping
    
    def _extract_position_from_filename(self, filename: str) -> str:
        """从文件名提取位置信息"""
        try:
            # 文件名格式: camera_001_zhuang_1.png
            parts = filename.split('_')
            if len(parts) >= 4:
                return f"{parts[2]}_{parts[3].split('.')[0]}"
            return "unknown"
        except:
            return "unknown"
    
    def _update_recognition_method_stats(self, camera_id: str, result: Dict[str, Any]):
        """更新识别方法统计"""
        try:
            method = result.get('method', 'unknown')
            hybrid_info = result.get('hybrid_info', {})
            used_methods = hybrid_info.get('used_methods', [])
            
            # 更新全局统计
            if method == 'yolo' and len(used_methods) == 1:
                self.stats['recognition_method_stats']['yolo_complete'] += 1
                self.stats['camera_stats'][camera_id]['recognition_method_counts']['yolo_complete'] += 1
            elif len(used_methods) > 1:
                self.stats['recognition_method_stats']['hybrid_combined'] += 1
                self.stats['camera_stats'][camera_id]['recognition_method_counts']['hybrid_combined'] += 1
            elif 'ocr' in used_methods:
                self.stats['recognition_method_stats']['ocr_only'] += 1
                self.stats['camera_stats'][camera_id]['recognition_method_counts']['ocr_only'] += 1
            elif 'opencv_suit' in used_methods:
                self.stats['recognition_method_stats']['opencv_only'] += 1
                self.stats['camera_stats'][camera_id]['recognition_method_counts']['opencv_only'] += 1
            else:
                self.stats['recognition_method_stats']['failed'] += 1
                
        except Exception:
            pass  # 忽略统计错误
    
    def _update_quality_stats(self, camera_id: str, quality_info: Dict[str, Any]):
        """更新质量统计"""
        try:
            quality_level = quality_info.get('quality_level', '').lower()
            quality_score = quality_info.get('quality_score', 0.0)
            
            # 更新全局质量统计
            quality_mapping = {
                '优秀': 'excellent',
                '良好': 'good', 
                '一般': 'average',
                '较差': 'poor',
                '很差': 'very_poor'
            }
            
            for chinese, english in quality_mapping.items():
                if chinese in quality_level:
                    self.stats['quality_stats'][english] += 1
                    break
            
            # 更新摄像头质量历史
            camera_stats = self.stats['camera_stats'][camera_id]
            camera_stats['quality_history'].append(quality_score)
            
            # 保持历史记录数量限制
            if len(camera_stats['quality_history']) > 10:
                camera_stats['quality_history'] = camera_stats['quality_history'][-10:]
            
            # 更新平均质量评分
            if camera_stats['quality_history']:
                camera_stats['average_quality_score'] = sum(camera_stats['quality_history']) / len(camera_stats['quality_history'])
                
        except Exception:
            pass  # 忽略统计错误
    
    def _format_recognition_results_simple(self, camera_id: str, position_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """简单格式化识别结果（不使用合并器）"""
        positions = {}
        
        # 标准位置列表
        standard_positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
        
        for position in standard_positions:
            if position in position_results and position_results[position]['success']:
                result = position_results[position]
                positions[position] = {
                    'suit': result.get('suit', ''),
                    'rank': result.get('rank', ''),
                    'confidence': result.get('confidence', 0.0)
                }
            else:
                positions[position] = {
                    'suit': '',
                    'rank': '',
                    'confidence': 0.0
                }
        
        return {
            'success': True,
            'camera_id': camera_id,
            'positions': positions,
            'timestamp': datetime.now().isoformat(),
            'merge_enabled': False
        }
    
    def _convert_merge_result_to_database_format(self, camera_id: str, merge_result: Dict[str, Any]) -> Dict[str, Any]:
        """将合并结果转换为数据库格式"""
        positions = {}
        
        # 从合并结果提取位置数据
        merge_positions = merge_result.get('positions', {})
        standard_positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
        
        for position in standard_positions:
            if position in merge_positions and merge_positions[position].get('success', False):
                result = merge_positions[position]
                positions[position] = {
                    'suit': result.get('suit', ''),
                    'rank': result.get('rank', ''),
                    'confidence': result.get('confidence', 0.0)
                }
            else:
                positions[position] = {
                    'suit': '',
                    'rank': '',
                    'confidence': 0.0
                }
        
        return {
            'success': True,
            'camera_id': camera_id,
            'positions': positions,
            'timestamp': merge_result.get('timestamp', datetime.now().isoformat()),
            'merge_enabled': True,
            'quality': merge_result.get('quality', {}),
            'summary': merge_result.get('summary', {}),
            'warnings': merge_result.get('warnings', [])
        }
    
    def run_main_loop(self):
        """运行主循环"""
        try:
            print(f"\n🔄 开始数据库版实时识别推送循环")
            print(f"   识别间隔: {self.config['recognition_interval']} 秒")
            print(f"   切换延迟: {self.config['camera_switch_delay']} 秒")
            print(f"   启用摄像头: {len(self.enabled_cameras)} 个")
            print(f"   融合策略: {self.recognition_config['fusion_strategy']}")
            print(f"   结果合并: {'启用' if self.config['enable_result_merging'] else '禁用'}")
            print(f"   数据库写入: {'启用' if self.config['enable_database'] else '禁用'}")
            print("=" * 60)
            
            while not self.shutdown_requested:
                cycle_start_time = time.time()
                self.stats['total_cycles'] += 1
                
                # 显示循环信息
                self._display_cycle_header()
                
                # 轮询处理每个摄像头
                for i, camera in enumerate(self.enabled_cameras):
                    if self.shutdown_requested:
                        break
                    
                    camera_id = camera['id']
                    camera_name = camera.get('name', f'摄像头{camera_id}')
                    
                    # 显示当前处理的摄像头
                    self._display_camera_processing(i + 1, len(self.enabled_cameras), camera_name, camera_id)
                    
                    # 执行完整流程
                    success = self._process_single_camera_workflow(camera_id)
                    
                    # 摄像头切换延迟
                    if i < len(self.enabled_cameras) - 1 and not self.shutdown_requested:
                        time.sleep(self.config['camera_switch_delay'])
                
                # 显示本轮统计
                cycle_duration = time.time() - cycle_start_time
                self._display_cycle_summary(cycle_duration)
                
                # 循环间隔
                remaining_time = max(0, self.config['recognition_interval'] - cycle_duration)
                if remaining_time > 0 and not self.shutdown_requested:
                    self._display_waiting(remaining_time)
                    time.sleep(remaining_time)
                    
        except KeyboardInterrupt:
            print("\n⏹️  接收到停止信号")
            self.shutdown_requested = True
        except Exception as e:
            print(f"\n❌ 主循环异常: {e}")
            self.shutdown_requested = True
        finally:
            # 关闭数据库连接
            if self.db_connection:
                self.db_connection.close()
                print("🗄️  数据库连接已关闭")
    
    def _process_single_camera_workflow(self, camera_id: str) -> bool:
        """处理单个摄像头的完整工作流程"""
        workflow_start_time = time.time()
        
        try:
            # 步骤2: 拍照
            photo_result = self.step2_take_photo(camera_id)
            
            if not photo_result['success']:
                self._display_step_result("拍照", False, photo_result['error'], photo_result['duration'])
                return False
            
            self._display_step_result("拍照", True, f"{photo_result['filename']} ({photo_result['file_size']/1024:.1f}KB)", photo_result['duration'])
            
            # 步骤3: 裁剪
            crop_result = self.step3_crop_images(photo_result['file_path'])
            
            if not crop_result['success']:
                self._display_step_result("裁剪", False, crop_result['error'], crop_result['duration'])
                return False
            
            self._display_step_result("裁剪", True, f"{crop_result['total_count']} 个区域", crop_result['duration'])
            
            # 步骤4: 混合识别
            recognition_result = self.step4_recognize_images_hybrid(
                camera_id, crop_result['main_files'], crop_result['left_files']
            )
            
            if not recognition_result['success']:
                self._display_step_result("混合识别", False, recognition_result.get('error', '识别失败'), recognition_result['duration'])
                return False
            
            # 显示识别结果
            self._display_recognition_results(camera_id, recognition_result)
            
            # 步骤5: 合并结果
            merge_result = self.step5_merge_results(camera_id, recognition_result['position_results'])
            
            if not merge_result['success']:
                self._display_step_result("结果合并", False, merge_result.get('error', '合并失败'), merge_result.get('duration', 0))
                return False
            
            # 显示合并结果
            self._display_merge_results(merge_result)
            
            # 保存最新结果
            self.stats['last_results'][camera_id] = merge_result
            
            # 步骤6: 写入数据库
            db_result = self.step6_write_to_database(camera_id, merge_result)
            self._display_step_result("数据库写入", db_result['success'], 
                                    f"{db_result['message']} ({db_result.get('updated_count', 0)}条)", 
                                    db_result['duration'])
            
            # 显示总耗时
            total_duration = time.time() - workflow_start_time
            print(f"      💫 总耗时: {total_duration:.2f}秒")
            
            return True
            
        except Exception as e:
            print(f"      ❌ 工作流程异常: {e}")
            return False
    
    def _display_cycle_header(self):
        """显示循环头部信息"""
        with self.display_lock:
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f"\n🔄 第 {self.stats['total_cycles']} 轮循环 ({current_time})")
            print("=" * 60)
    
    def _display_camera_processing(self, current: int, total: int, camera_name: str, camera_id: str):
        """显示当前处理的摄像头"""
        with self.display_lock:
            print(f"\n📷 ({current}/{total}) {camera_name} (ID: {camera_id})")
            print("-" * 40)
    
    def _display_step_result(self, step_name: str, success: bool, message: str, duration: float):
        """显示步骤结果"""
        with self.display_lock:
            status_icon = "✅" if success else "❌"
            print(f"      {status_icon} {step_name}: {message} ({duration:.2f}s)")
    
    def _display_recognition_results(self, camera_id: str, recognition_result: Dict[str, Any]):
        """显示混合识别结果"""
        with self.display_lock:
            success_count = recognition_result['successful_count']
            total_count = recognition_result['total_count']
            success_rate = recognition_result['success_rate']
            duration = recognition_result['duration']
            
            print(f"      ✅ 混合识别: {success_count}/{total_count} 成功 ({success_rate:.1f}%) ({duration:.2f}s)")
            
            # 显示具体识别结果和方法
            position_results = recognition_result['position_results']
            position_names = {
                'zhuang_1': '庄1', 'zhuang_2': '庄2', 'zhuang_3': '庄3',
                'xian_1': '闲1', 'xian_2': '闲2', 'xian_3': '闲3'
            }
            
            recognized_cards = []
            method_counts = {'yolo': 0, 'hybrid': 0, 'ocr': 0, 'opencv': 0}
            
            for position, result in position_results.items():
                if result['success']:
                    pos_name = position_names.get(position, position)
                    display_name = result.get('display_name', 'N/A')
                    confidence = result.get('confidence', 0)
                    
                    # 统计识别方法
                    hybrid_info = result.get('hybrid_info', {})
                    used_methods = hybrid_info.get('used_methods', [])
                    
                    if len(used_methods) == 1 and 'yolo' in used_methods:
                        method_counts['yolo'] += 1
                        method_indicator = 'Y'
                    elif len(used_methods) > 1:
                        method_counts['hybrid'] += 1
                        method_indicator = 'H'
                    elif 'ocr' in used_methods:
                        method_counts['ocr'] += 1
                        method_indicator = 'O'
                    elif 'opencv_suit' in used_methods:
                        method_counts['opencv'] += 1
                        method_indicator = 'C'
                    else:
                        method_indicator = '?'
                    
                    recognized_cards.append(f"{pos_name}:{display_name}({confidence:.2f})[{method_indicator}]")
            
            if recognized_cards:
                cards_str = " | ".join(recognized_cards)
                print(f"         🎴 {cards_str}")
                
                # 显示方法统计
                method_summary = []
                if method_counts['yolo'] > 0:
                    method_summary.append(f"YOLO:{method_counts['yolo']}")
                if method_counts['hybrid'] > 0:
                    method_summary.append(f"混合:{method_counts['hybrid']}")
                if method_counts['ocr'] > 0:
                    method_summary.append(f"OCR:{method_counts['ocr']}")
                if method_counts['opencv'] > 0:
                    method_summary.append(f"CV:{method_counts['opencv']}")
                
                if method_summary:
                    print(f"         🧠 方法: {' | '.join(method_summary)}")
    
    def _display_merge_results(self, merge_result: Dict[str, Any]):
        """显示合并结果"""
        with self.display_lock:
            if merge_result.get('merge_enabled', False):
                duration = merge_result.get('merge_duration', 0)
                print(f"      ✅ 结果合并: 完成 ({duration:.3f}s)")
                
                # 显示质量信息
                if 'quality' in merge_result:
                    quality = merge_result['quality']
                    quality_level = quality.get('quality_level', 'N/A')
                    quality_score = quality.get('quality_score', 0)
                    print(f"         🏆 质量: {quality_level} ({quality_score:.3f})")
                
                # 显示警告
                warnings = merge_result.get('warnings', [])
                if warnings:
                    print(f"         ⚠️  警告: {'; '.join(warnings)}")
            else:
                print(f"      ⚪ 结果合并: 已禁用")
    
    def _display_cycle_summary(self, cycle_duration: float):
        """显示循环汇总"""
        with self.display_lock:
            print(f"\n📊 本轮汇总: 耗时 {cycle_duration:.2f}秒")
            
            # 显示数据库统计
            db_stats = self.stats['database_stats']
            db_success_rate = (db_stats['successful_writes'] / db_stats['total_writes'] * 100) if db_stats['total_writes'] > 0 else 0
            print(f"   🗄️  数据库: 总写入{db_stats['total_writes']} 成功{db_stats['successful_writes']} 失败{db_stats['failed_writes']} 成功率{db_success_rate:.1f}% 初始化{db_stats['successful_initializations']} 连接错误{db_stats['connection_errors']}")
            
            # 显示各摄像头状态
            for camera_id, stats in self.stats['camera_stats'].items():
                camera_name = next((c['name'] for c in self.enabled_cameras if c['id'] == camera_id), camera_id)
                
                success_icon = "✅" if stats['successful_recognitions'] > 0 else "⚪"
                last_time = stats.get('last_recognition_time', '未知')
                avg_quality = stats.get('average_quality_score', 0)
                table_id = stats.get('table_id', 1)
                init_status = "✓" if stats.get('data_initialized', False) else "○"
                
                # 识别方法统计
                method_counts = stats['recognition_method_counts']
                method_str = f"Y{method_counts['yolo_complete']}H{method_counts['hybrid_combined']}O{method_counts['ocr_only']}C{method_counts['opencv_only']}"
                
                print(f"   {success_icon} {camera_name}: 拍照{stats['successful_photos']}/{stats['total_attempts']} "
                      f"识别{stats['successful_recognitions']} 写入{stats['successful_writes']} "
                      f"质量{avg_quality:.2f} 方法[{method_str}] 表ID{table_id} 初始化{init_status} 最后:{last_time}")
    
    def _display_waiting(self, wait_time: float):
        """显示等待信息"""
        with self.display_lock:
            print(f"⏳ 等待 {wait_time:.1f}秒 后开始下轮循环...")
    
    def display_final_statistics(self):
        """显示最终统计"""
        try:
            print("\n📈 最终运行统计")
            print("=" * 50)
            
            # 计算运行时间
            total_time = datetime.now() - self.stats['start_time']
            print(f"⏰ 总运行时间: {str(total_time).split('.')[0]}")
            print(f"🔄 总循环数: {self.stats['total_cycles']}")
            
            # 显示数据库统计
            db_stats = self.stats['database_stats']
            if db_stats['total_writes'] > 0:
                db_success_rate = (db_stats['successful_writes'] / db_stats['total_writes']) * 100
                print(f"\n🗄️  数据库统计:")
                print(f"  总写入次数: {db_stats['total_writes']}")
                print(f"  成功写入: {db_stats['successful_writes']} ({db_success_rate:.1f}%)")
                print(f"  失败写入: {db_stats['failed_writes']}")
                print(f"  数据初始化: {db_stats['successful_initializations']}/{db_stats['total_initializations']}")
                print(f"  连接错误: {db_stats['connection_errors']}")
                print(f"  最后写入: {db_stats['last_write_time'] or '无'}")
            
            # 显示识别方法统计
            method_stats = self.stats['recognition_method_stats']
            total_recognitions = sum(method_stats.values())
            if total_recognitions > 0:
                print(f"\n🧠 识别方法统计 (总计: {total_recognitions} 次):")
                method_names = {
                    'yolo_complete': 'YOLO完整识别',
                    'hybrid_combined': '混合组合识别',
                    'ocr_only': '仅OCR识别',
                    'opencv_only': '仅OpenCV识别',
                    'failed': '识别失败'
                }
                for method, count in method_stats.items():
                    if count > 0:
                        percentage = (count / total_recognitions) * 100
                        method_name = method_names.get(method, method)
                        print(f"  {method_name}: {count} 次 ({percentage:.1f}%)")
            
            # 显示质量统计
            quality_stats = self.stats['quality_stats']
            total_quality = sum(quality_stats.values())
            if total_quality > 0:
                print(f"\n🏆 质量等级统计 (总计: {total_quality} 次):")
                quality_names = {
                    'excellent': '优秀',
                    'good': '良好',
                    'average': '一般',
                    'poor': '较差',
                    'very_poor': '很差'
                }
                for level, count in quality_stats.items():
                    if count > 0:
                        percentage = (count / total_quality) * 100
                        level_name = quality_names.get(level, level)
                        print(f"  {level_name}: {count} 次 ({percentage:.1f}%)")
            
            print(f"\n📷 各摄像头详细统计:")
            for camera_id, stats in self.stats['camera_stats'].items():
                camera_name = next((c['name'] for c in self.enabled_cameras if c['id'] == camera_id), camera_id)
                
                photo_rate = (stats['successful_photos'] / stats['total_attempts'] * 100) if stats['total_attempts'] > 0 else 0
                
                print(f"   {camera_name} (ID: {camera_id}, tableId: {stats.get('table_id', 1)}):")
                print(f"     拍照: {stats['successful_photos']}/{stats['total_attempts']} ({photo_rate:.1f}%)")
                print(f"     识别: {stats['successful_recognitions']} 次成功")
                print(f"     写入: {stats['successful_writes']} 次成功")
                print(f"     数据初始化: {'是' if stats.get('data_initialized', False) else '否'}")
                print(f"     平均质量: {stats['average_quality_score']:.3f}")
                
                # 识别方法分布
                method_counts = stats['recognition_method_counts']
                method_items = [f"{k}:{v}" for k, v in method_counts.items() if v > 0]
                if method_items:
                    print(f"     方法分布: {', '.join(method_items)}")
            
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ 显示统计信息失败: {e}")


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='数据库版实时识别推送系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python tui.py                           # 默认配置运行
  python tui.py --interval 5              # 设置循环间隔为5秒
  python tui.py --no-db                   # 禁用数据库写入功能
  python tui.py --strategy voting         # 使用投票融合策略
  python tui.py --no-merge                # 禁用结果合并
  python tui.py --no-yolo                 # 禁用YOLO识别
  python tui.py --debug                   # 启用调试模式
        """
    )
    
    parser.add_argument('--interval', type=int, default=3,
                       help='识别循环间隔(秒) (默认: 3)')
    parser.add_argument('--camera-delay', type=float, default=1.0,
                       help='摄像头切换延迟(秒) (默认: 1.0)')
    parser.add_argument('--max-retries', type=int, default=3,
                       help='最大重试次数 (默认: 3)')
    parser.add_argument('--no-db', action='store_true',
                       help='禁用数据库写入功能')
    parser.add_argument('--no-merge', action='store_true',
                       help='禁用结果合并')
    parser.add_argument('--strategy', choices=['weighted', 'voting', 'priority'], 
                       default='weighted', help='融合策略 (默认: weighted)')
    parser.add_argument('--debug', action='store_true',
                       help='启用调试模式')
    parser.add_argument('--no-yolo', action='store_true',
                       help='禁用YOLO识别')
    parser.add_argument('--no-ocr', action='store_true',
                       help='禁用OCR识别')
    parser.add_argument('--no-opencv', action='store_true',
                       help='禁用OpenCV花色识别')
    
    return parser.parse_args()


def main():
    """主函数"""
    try:
        args = parse_arguments()
        
        # 创建数据库版系统实例
        system = DatabaseTuiSystem()
        
        # 更新系统配置
        system.config.update({
            'recognition_interval': args.interval,
            'camera_switch_delay': args.camera_delay,
            'max_retry_times': args.max_retries,
            'enable_database': not args.no_db,
            'enable_result_merging': not args.no_merge,
        })
        
        # 更新识别配置
        system.recognition_config.update({
            'fusion_strategy': args.strategy,
            'debug_mode': args.debug,
            'yolo_enabled': not args.no_yolo,
            'ocr_enabled': not args.no_ocr,
            'opencv_suit_enabled': not args.no_opencv
        })
        
        # 步骤1: 读取摄像头配置
        if not system.step1_load_camera_config():
            return 1
        
        # 初始化数据库连接
        if system.config['enable_database']:
            if not system._init_database_connection():
                print("❌ 数据库连接初始化失败，程序退出")
                return 1
        
        # 显示系统配置
        print(f"\n🚀 数据库版系统配置:")
        print(f"   循环间隔: {system.config['recognition_interval']} 秒")
        print(f"   切换延迟: {system.config['camera_switch_delay']} 秒")
        print(f"   最大重试: {system.config['max_retry_times']} 次")
        print(f"   数据库写入: {'启用' if system.config['enable_database'] else '禁用'}")
        print(f"   结果合并: {'启用' if system.config['enable_result_merging'] else '禁用'}")
        print(f"   融合策略: {system.recognition_config['fusion_strategy']}")
        print(f"   YOLO识别: {'启用' if system.recognition_config['yolo_enabled'] else '禁用'}")
        print(f"   OCR识别: {'启用' if system.recognition_config['ocr_enabled'] else '禁用'}")
        print(f"   OpenCV识别: {'启用' if system.recognition_config['opencv_suit_enabled'] else '禁用'}")
        print(f"   调试模式: {'启用' if system.recognition_config['debug_mode'] else '禁用'}")
        
        # 设置信号处理
        def signal_handler(signum, frame):
            print(f"\n📡 接收到信号 {signum}，准备关闭系统...")
            system.shutdown_requested = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        print("\n🔄 按 Ctrl+C 停止系统")
        
        # 运行主循环
        system.run_main_loop()
        
        # 显示最终统计
        if system.stats['total_cycles'] > 0:
            system.display_final_statistics()
        
        print("👋 数据库版实时识别推送系统已关闭")
        
        return 0
        
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())