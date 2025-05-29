#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版实时识别推送系统 - tui.py
业务逻辑:
1. 读取摄像头配置
2. 循环调用 see.py 进行完整识别
3. 转换结果格式并写入数据库
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

class SimplifiedTuiSystem:
    """简化版实时推送系统"""
    
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
        
        # 位置映射配置 (系统格式 -> 数据库格式)
        self.position_mapping = {
            'zhuang_1': 't1_pl0',
            'zhuang_2': 't1_pl1', 
            'zhuang_3': 't1_pl2',
            'xian_1': 't1_pr0',
            'xian_2': 't1_pr1',
            'xian_3': 't1_pr2'
        }
        
        # 摄像头配置
        self.enabled_cameras = []
        
        # 数据库连接
        self.db_connection = None
        
        # 统计信息
        self.stats = {
            'start_time': datetime.now(),
            'total_cycles': 0,
            'camera_stats': {},
            'database_stats': {
                'total_writes': 0,
                'successful_writes': 0,
                'failed_writes': 0,
                'connection_errors': 0,
                'last_write_time': None
            },
            'recognition_stats': {
                'total_recognitions': 0,
                'successful_recognitions': 0,
                'failed_recognitions': 0,
                'average_processing_time': 0.0,
                'total_processing_time': 0.0
            }
        }
        
        # 显示状态
        self.display_lock = threading.Lock()
        
        print("🚀 简化版数据库推送系统初始化完成")
    
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
                    'successful_recognitions': 0,
                    'failed_recognitions': 0,
                    'successful_writes': 0,
                    'failed_writes': 0,
                    'table_id': table_id,
                    'last_recognition_time': None,
                    'last_result': None,
                    'average_processing_time': 0.0,
                    'total_processing_time': 0.0
                }
                
                print(f"   {i+1}. {camera['name']} (ID: {camera_id}, tableId: {table_id}) - IP: {camera['ip']}")
            
            return True
            
        except Exception as e:
            print(f"❌ 读取摄像头配置失败: {e}")
            return False
    
    def step2_recognize_camera(self, camera_id: str) -> Dict[str, Any]:
        """步骤2: 使用 see.py 进行完整识别"""
        try:
            print(f"   🧠 调用 see.py 识别...")
            
            # 导入 see.py 的识别函数
            from src.processors.see import recognize_camera
            
            # 记录开始时间
            start_time = time.time()
            
            # 一行代码完成：拍照 → 切图 → 混合识别 → 结果汇总
            result = recognize_camera(camera_id)
            
            # 计算耗时
            duration = time.time() - start_time
            result['actual_duration'] = duration
            
            # 更新统计信息
            self._update_recognition_stats(camera_id, result, duration)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'camera_id': camera_id,
                'error': str(e),
                'actual_duration': 0.0
            }
    
    def step3_convert_to_database_format(self, recognition_result: Dict[str, Any]) -> Dict[str, Any]:
        """步骤3: 转换为数据库格式"""
        try:
            if not recognition_result.get('success', False):
                return {'success': False, 'message': '识别结果无效'}
            
            positions = recognition_result.get('positions', {})
            db_positions = {}
            
            # 转换每个位置的结果
            for system_pos, db_pos in self.position_mapping.items():
                pos_result = positions.get(system_pos, {})
                
                if pos_result.get('success', False):
                    # 解析卡牌信息
                    card = pos_result.get('card', '')
                    suit, rank = self._parse_card_info(card)
                else:
                    # 识别失败的位置
                    suit, rank = '0', '0'
                
                db_positions[db_pos] = {
                    'suit': suit,
                    'rank': rank,
                    'confidence': pos_result.get('confidence', 0.0),
                    'success': pos_result.get('success', False)
                }
            
            return {
                'success': True,
                'positions': db_positions,
                'message': f'转换完成，{len(db_positions)} 个位置'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'格式转换失败: {str(e)}'
            }
    
    def step4_write_to_database(self, camera_id: str, db_data: Dict[str, Any]) -> Dict[str, Any]:
        """步骤4: 写入数据库"""
        try:
            if not self.config['enable_database']:
                return {'success': True, 'message': '数据库写入已禁用', 'updated_count': 0}
            
            start_time = time.time()
            
            # 确保数据库连接有效
            if not self._ensure_database_connection():
                return {
                    'success': False, 
                    'message': '数据库连接失败',
                    'updated_count': 0
                }
            
            # 获取tableId
            table_id = self._get_table_id_from_config(camera_id)
            
            # 检查并初始化摄像头数据
            if not self._camera_data_exists(camera_id, table_id):
                if not self._insert_initial_camera_data(camera_id, table_id):
                    return {
                        'success': False,
                        'message': '初始化摄像头数据失败',
                        'updated_count': 0
                    }
            
            # 显示识别结果
            self._display_recognition_results(camera_id, db_data, table_id)
            
            # 更新数据库
            update_result = self._update_camera_results(camera_id, table_id, db_data)
            
            # 更新统计
            duration = time.time() - start_time
            self.stats['database_stats']['total_writes'] += 1
            
            if update_result['success']:
                self.stats['database_stats']['successful_writes'] += 1
                self.stats['database_stats']['last_write_time'] = datetime.now().strftime('%H:%M:%S')
                self.stats['camera_stats'][camera_id]['successful_writes'] += 1
            else:
                self.stats['database_stats']['failed_writes'] += 1
                self.stats['camera_stats'][camera_id]['failed_writes'] += 1
            
            update_result['duration'] = duration
            return update_result
            
        except Exception as e:
            self.stats['database_stats']['failed_writes'] += 1
            self.stats['camera_stats'][camera_id]['failed_writes'] += 1
            return {
                'success': False,
                'message': str(e),
                'updated_count': 0
            }
    
    def _parse_card_info(self, card_str: str) -> tuple:
        """解析卡牌字符串，返回花色和点数的数字编码"""
        try:
            if not card_str or card_str == "未知":
                return '0', '0'
            
            # 花色映射
            suit_mapping = {
                '♠️': '1', '♠': '1',  # 黑桃
                '♥️': '2', '♥': '2',  # 红桃  
                '♣️': '3', '♣': '3',  # 梅花
                '♦️': '4', '♦': '4'   # 方块
            }
            
            # 点数映射
            rank_mapping = {
                'A': '1', '2': '2', '3': '3', '4': '4', '5': '5',
                '6': '6', '7': '7', '8': '8', '9': '9', '10': '10',
                'J': '11', 'Q': '12', 'K': '13'
            }
            
            # 提取花色符号
            suit_char = None
            rank_part = card_str
            
            for symbol, code in suit_mapping.items():
                if symbol in card_str:
                    suit_char = code
                    rank_part = card_str.replace(symbol, '').strip()
                    break
            
            # 提取点数
            rank_char = rank_mapping.get(rank_part, '0')
            
            return suit_char or '0', rank_char
            
        except Exception as e:
            print(f"⚠️  解析卡牌失败 '{card_str}': {e}")
            return '0', '0'
    
    def _get_table_id_from_config(self, camera_id: str) -> int:
        """从配置获取tableId"""
        try:
            for camera in self.enabled_cameras:
                if camera.get('id') == camera_id:
                    return int(camera.get('tableId', 1))
            return 1
        except Exception:
            return 1
    
    def _camera_data_exists(self, camera_id: str, table_id: int) -> bool:
        """检查摄像头数据是否存在"""
        try:
            with self.db_connection.cursor() as cursor:
                sql = "SELECT COUNT(*) FROM tu_bjl_result WHERE camera_id = %s AND tableId = %s"
                cursor.execute(sql, (camera_id, table_id))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception:
            return False
    
    def _insert_initial_camera_data(self, camera_id: str, table_id: int) -> bool:
        """插入摄像头的初始6条记录"""
        try:
            print(f"      🔧 初始化摄像头 {camera_id} 数据 (tableId: {table_id})")
            
            initial_records = []
            for db_position in ['t1_pl0', 't1_pl1', 't1_pl2', 't1_pr0', 't1_pr1', 't1_pr2']:
                initial_records.append((
                    db_position,
                    '{"rank": "0", "suit": "0"}',
                    camera_id,
                    table_id
                ))
            
            with self.db_connection.cursor() as cursor:
                sql = "INSERT INTO tu_bjl_result (position, result, camera_id, tableId) VALUES (%s, %s, %s, %s)"
                cursor.executemany(sql, initial_records)
            
            self.db_connection.commit()
            print(f"      ✅ 成功初始化 {len(initial_records)} 条记录")
            return True
            
        except Exception as e:
            if self.db_connection:
                self.db_connection.rollback()
            print(f"      ❌ 初始化摄像头数据失败: {e}")
            return False
    
    def _update_camera_results(self, camera_id: str, table_id: int, db_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新摄像头识别结果到数据库"""
        try:
            positions = db_data.get('positions', {})
            updated_count = 0
            
            with self.db_connection.cursor() as cursor:
                for db_position, position_data in positions.items():
                    # 构建JSON字符串
                    result_json = json.dumps({
                        "rank": position_data.get('rank', '0'),
                        "suit": position_data.get('suit', '0')
                    })
                    
                    # 执行更新
                    sql = "UPDATE tu_bjl_result SET result = %s WHERE camera_id = %s AND tableId = %s AND position = %s"
                    cursor.execute(sql, (result_json, camera_id, table_id, db_position))
                    
                    if cursor.rowcount > 0:
                        updated_count += 1
            
            self.db_connection.commit()
            
            return {
                'success': True,
                'message': f'成功更新 {updated_count} 条记录',
                'updated_count': updated_count
            }
            
        except Exception as e:
            if self.db_connection:
                self.db_connection.rollback()
            
            return {
                'success': False,
                'message': f'数据库更新失败: {str(e)}',
                'updated_count': 0
            }
    
    def _display_recognition_results(self, camera_id: str, db_data: Dict[str, Any], table_id: int):
        """显示识别结果"""
        with self.display_lock:
            positions = db_data.get('positions', {})
            
            print(f"      📊 识别结果 (camera_id: {camera_id}, tableId: {table_id}):")
            print("      ┌─────────┬─────────┬────────┬─────────┬──────────┐")
            print("      │ 数据库位置│ 系统位置│ 转换结果│ 置信度  │ 状态     │")
            print("      ├─────────┼─────────┼────────┼─────────┼──────────┤")
            
            for db_position in ['t1_pl0', 't1_pl1', 't1_pl2', 't1_pr0', 't1_pr1', 't1_pr2']:
                # 找到对应的系统位置
                system_position = None
                for sys_pos, db_pos in self.position_mapping.items():
                    if db_pos == db_position:
                        system_position = sys_pos
                        break
                
                pos_data = positions.get(db_position, {})
                suit = pos_data.get('suit', '0')
                rank = pos_data.get('rank', '0')
                confidence = pos_data.get('confidence', 0.0)
                success = pos_data.get('success', False)
                
                converted_result = f"{suit},{rank}"
                confidence_str = f"{confidence*100:.1f}%" if confidence > 0 else "0.0%"
                status = "成功" if success else "失败"
                
                # 简化系统位置显示
                system_pos_short = system_position.replace('zhuang_', '庄').replace('xian_', '闲') if system_position else "未知"
                
                print(f"      │ {db_position:<7} │ {system_pos_short:<7} │ {converted_result:<6} │ {confidence_str:<7} │ {status:<8} │")
            
            print("      └─────────┴─────────┴────────┴─────────┴──────────┘")
    
    def _update_recognition_stats(self, camera_id: str, result: Dict[str, Any], duration: float):
        """更新识别统计信息"""
        try:
            # 更新摄像头统计
            stats = self.stats['camera_stats'][camera_id]
            stats['total_attempts'] += 1
            stats['total_processing_time'] += duration
            stats['average_processing_time'] = stats['total_processing_time'] / stats['total_attempts']
            
            if result.get('success', False):
                stats['successful_recognitions'] += 1
                stats['last_recognition_time'] = datetime.now().strftime('%H:%M:%S')
                stats['last_result'] = result
            else:
                stats['failed_recognitions'] += 1
            
            # 更新全局统计
            global_stats = self.stats['recognition_stats']
            global_stats['total_recognitions'] += 1
            global_stats['total_processing_time'] += duration
            global_stats['average_processing_time'] = global_stats['total_processing_time'] / global_stats['total_recognitions']
            
            if result.get('success', False):
                global_stats['successful_recognitions'] += 1
            else:
                global_stats['failed_recognitions'] += 1
                
        except Exception as e:
            print(f"⚠️  更新统计失败: {e}")
    
    def run_main_loop(self):
        """运行主循环"""
        try:
            print(f"\n🔄 开始简化版数据库推送循环")
            print(f"   识别间隔: {self.config['recognition_interval']} 秒")
            print(f"   切换延迟: {self.config['camera_switch_delay']} 秒")
            print(f"   启用摄像头: {len(self.enabled_cameras)} 个")
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
                    self._process_single_camera_workflow(camera_id)
                    
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
            # 步骤2: 使用 see.py 进行完整识别
            recognition_result = self.step2_recognize_camera(camera_id)
            
            if not recognition_result.get('success', False):
                self._display_step_result("see.py识别", False, 
                                        recognition_result.get('error', '识别失败'), 
                                        recognition_result.get('actual_duration', 0))
                return False
            
            # 显示识别成功信息
            self._display_recognition_success(camera_id, recognition_result)
            
            # 步骤3: 转换为数据库格式
            convert_result = self.step3_convert_to_database_format(recognition_result)
            
            if not convert_result['success']:
                self._display_step_result("格式转换", False, convert_result['message'], 0)
                return False
            
            self._display_step_result("格式转换", True, convert_result['message'], 0)
            
            # 步骤4: 写入数据库
            db_result = self.step4_write_to_database(camera_id, convert_result)
            self._display_step_result("数据库写入", db_result['success'], 
                                    f"{db_result['message']} ({db_result.get('updated_count', 0)}条)", 
                                    db_result.get('duration', 0))
            
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
            if duration > 0:
                print(f"      {status_icon} {step_name}: {message} ({duration:.2f}s)")
            else:
                print(f"      {status_icon} {step_name}: {message}")
    
    def _display_recognition_success(self, camera_id: str, result: Dict[str, Any]):
        """显示识别成功信息"""
        with self.display_lock:
            summary = result.get('summary', {})
            successful = summary.get('successful', 0)
            total = summary.get('total', 6)
            success_rate = summary.get('success_rate', '0%')
            duration = result.get('processing_time', 0)
            
            print(f"      ✅ see.py识别: {successful}/{total} 成功 ({success_rate}) ({duration:.2f}s)")
            
            # 显示识别的卡牌
            cards = summary.get('cards', [])
            if cards:
                cards_str = ', '.join(cards[:3]) + ('...' if len(cards) > 3 else '')
                print(f"         🃏 识别卡牌: {cards_str}")
    
    def _display_cycle_summary(self, cycle_duration: float):
        """显示循环汇总"""
        with self.display_lock:
            print(f"\n📊 本轮汇总: 耗时 {cycle_duration:.2f}秒")
            
            # 显示数据库统计
            db_stats = self.stats['database_stats']
            db_success_rate = (db_stats['successful_writes'] / db_stats['total_writes'] * 100) if db_stats['total_writes'] > 0 else 0
            print(f"   🗄️  数据库: 总写入{db_stats['total_writes']} 成功{db_stats['successful_writes']} 失败{db_stats['failed_writes']} 成功率{db_success_rate:.1f}% 连接错误{db_stats['connection_errors']}")
            
            # 显示识别统计
            rec_stats = self.stats['recognition_stats']
            rec_success_rate = (rec_stats['successful_recognitions'] / rec_stats['total_recognitions'] * 100) if rec_stats['total_recognitions'] > 0 else 0
            print(f"   🧠 识别: 总计{rec_stats['total_recognitions']} 成功{rec_stats['successful_recognitions']} 失败{rec_stats['failed_recognitions']} 成功率{rec_success_rate:.1f}% 平均{rec_stats['average_processing_time']:.2f}s")
            
            # 显示各摄像头状态
            for camera_id, stats in self.stats['camera_stats'].items():
                camera_name = next((c['name'] for c in self.enabled_cameras if c['id'] == camera_id), camera_id)
                
                rec_success_rate = (stats['successful_recognitions'] / stats['total_attempts'] * 100) if stats['total_attempts'] > 0 else 0
                write_success_rate = (stats['successful_writes'] / (stats['successful_writes'] + stats['failed_writes']) * 100) if (stats['successful_writes'] + stats['failed_writes']) > 0 else 0
                last_time = stats.get('last_recognition_time', '未知')
                avg_duration = stats.get('average_processing_time', 0)
                table_id = stats.get('table_id', 1)
                
                status_icon = "✅" if stats['successful_recognitions'] > 0 else "⚪"
                
                print(f"   {status_icon} {camera_name}: 识别{stats['successful_recognitions']}/{stats['total_attempts']}({rec_success_rate:.0f}%) "
                      f"写入{stats['successful_writes']}({write_success_rate:.0f}%) 平均{avg_duration:.2f}s "
                      f"表ID{table_id} 最后:{last_time}")
    
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
                print(f"  连接错误: {db_stats['connection_errors']}")
                print(f"  最后写入: {db_stats['last_write_time'] or '无'}")
            
            # 显示识别统计
            rec_stats = self.stats['recognition_stats']
            if rec_stats['total_recognitions'] > 0:
                rec_success_rate = (rec_stats['successful_recognitions'] / rec_stats['total_recognitions']) * 100
                print(f"\n🧠 识别统计:")
                print(f"  总识别次数: {rec_stats['total_recognitions']}")
                print(f"  成功识别: {rec_stats['successful_recognitions']} ({rec_success_rate:.1f}%)")
                print(f"  失败识别: {rec_stats['failed_recognitions']}")
                print(f"  平均耗时: {rec_stats['average_processing_time']:.2f}秒")
                print(f"  总耗时: {rec_stats['total_processing_time']:.2f}秒")
            
            print(f"\n📷 各摄像头详细统计:")
            for camera_id, stats in self.stats['camera_stats'].items():
                camera_name = next((c['name'] for c in self.enabled_cameras if c['id'] == camera_id), camera_id)
                
                rec_rate = (stats['successful_recognitions'] / stats['total_attempts'] * 100) if stats['total_attempts'] > 0 else 0
                write_rate = (stats['successful_writes'] / (stats['successful_writes'] + stats['failed_writes']) * 100) if (stats['successful_writes'] + stats['failed_writes']) > 0 else 0
                
                print(f"   {camera_name} (ID: {camera_id}, tableId: {stats.get('table_id', 1)}):")
                print(f"     识别: {stats['successful_recognitions']}/{stats['total_attempts']} ({rec_rate:.1f}%)")
                print(f"     写入: {stats['successful_writes']}/{stats['successful_writes'] + stats['failed_writes']} ({write_rate:.1f}%)")
                print(f"     平均耗时: {stats['average_processing_time']:.2f}秒")
            
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ 显示统计信息失败: {e}")


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='简化版数据库推送系统 (基于 see.py)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python tui.py                           # 默认配置运行
  python tui.py --interval 5              # 设置循环间隔为5秒
  python tui.py --no-db                   # 禁用数据库写入功能
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
    
    return parser.parse_args()


def main():
    """主函数"""
    try:
        args = parse_arguments()
        
        # 创建简化版系统实例
        system = SimplifiedTuiSystem()
        
        # 更新系统配置
        system.config.update({
            'recognition_interval': args.interval,
            'camera_switch_delay': args.camera_delay,
            'max_retry_times': args.max_retries,
            'enable_database': not args.no_db,
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
        print(f"\n🚀 简化版数据库系统配置:")
        print(f"   循环间隔: {system.config['recognition_interval']} 秒")
        print(f"   切换延迟: {system.config['camera_switch_delay']} 秒")
        print(f"   最大重试: {system.config['max_retry_times']} 次")
        print(f"   数据库写入: {'启用' if system.config['enable_database'] else '禁用'}")
        print(f"   核心识别: see.py (拍照→切图→混合识别)")
        
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
        
        print("👋 简化版数据库推送系统已关闭")
        
        return 0
        
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())