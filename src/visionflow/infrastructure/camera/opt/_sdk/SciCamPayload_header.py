import ctypes
import enum
import os

from ctypes import *
from enum import Enum
from enum import IntEnum

from visionflow.infrastructure.camera.native import (
	SDK_DLL_NAME,
	ensure_native_lib_path,
	resolve_opt_lib_dir,
)


def _load_scicam_sdk() -> ctypes.CDLL:
	# Carrega SciCamSDK.dll (runtime embutido ou OPT instalado).
	ensure_native_lib_path()
	lib_dir = resolve_opt_lib_dir()
	if lib_dir is None:
		raise FileNotFoundError(
			"SciCamSDK.dll não encontrado. Execute: python scripts/sync_opt_runtime.py "
			"ou instale o runtime OPT Machine Vision."
		)
	lib_path = lib_dir / SDK_DLL_NAME
	load_kwargs = {"winmode": 0x8} if os.name == "nt" else {}
	return ctypes.CDLL(str(lib_path), **load_kwargs)


class _LazySciCamDll:
	"""Proxy que carrega a DLL na primeira utilização (evita I/O no import)."""

	def __init__(self) -> None:
		self._dll: ctypes.CDLL | None = None

	def _get(self) -> ctypes.CDLL:
		if self._dll is None:
			self._dll = _load_scicam_sdk()
		return self._dll

	def __getattr__(self, name: str):
		return getattr(self._get(), name)


SciCamCtrlDll = _LazySciCamDll()

## @~chinese
#  @brief ��������
#  @~english
#  @brief Pixel type
class SciCamPixelType(IntEnum):
	#  @brief unknown
	PixelTypeUnknown = 0
	#  @brief Monochrome 1-bit per pixel
	Mono1p = 0x01010037
	#  @brief Monochrome 2-bit per pixel
	Mono2p = 0x01020038
	#  @brief Monochrome 4-bit per pixel
	Mono4p = 0x01040039
	#  @brief Monochrome 8-bit signed integer per pixel
	Mono8s = 0x01080002
	#  @brief Monochrome 8-bit
	Mono8 = 0x01080001
	#  @brief Monochrome 10-bit unpacked  
	Mono10 = 0x01100003
	#  @brief Monochrome 10-bit packed
	Mono10p = 0x010a0046
	#  @brief Monochrome 12-bit unpacked
	Mono12 = 0x01100005
	#  @brief Monochrome 12-bit packed
	Mono12p = 0x010c0047
	#  @brief Monochrome 14-bit
	Mono14 = 0x01100025
	#  @brief Monochrome 16-bit
	Mono16 = 0x01100007
	#  @brief Red-Green-Blue 8-bit
	RGB8 = 0x02180014
	#  @brief Blue-Green-Red 8-bit
	BGR8 = 0x02180015
	#  @brief Bayer Green-Red 8-bit
	BayerGR8 = 0x01080008
	#  @brief Bayer Red-Green 8-bit
	BayerRG8 = 0x01080009
	#  @brief Bayer Green-Blue 8-bit
	BayerGB8 = 0x0108000A
	#  @brief Bayer Blue-Green 8-bit
	BayerBG8 = 0x0108000B
	#  @brief YUV 4:1:1 8-bit
	YUV411_8_UYYVYY = 0x020C001E
	#  @brief YUV 4:2:2 8-bit
	YUV422_8_UYVY = 0x0210001F
	#  @brief YUV 4:4:4 8-bit
	YUV8_UYV = 0x02180020
	#  @brief YCbCr 4:4:4 8-bit BT.709
	YCbCr709_8_CbYCr = 0x02180040
	#  @brief YCbCr 4:2:2 8-bit BT.709
	YCbCr709_422_8 = 0x02100041
	#  @brief YUV 4:2:2 8-bit
	YUV422_8 = 0x02100032
	#  @brief Red-Green-Blue 5/6/5-bit packed
	RGB565p = 0x02100035
	#  @brief Blue-Green-Red 5/6/5-bit packed
	BGR565p = 0x02100036
	#  @brief GigE Vision 2.0 Monochrome 10 - bit packed
	Mono10Packed = 0x010C0004
	#  @brief GigE Vision 2.0 Monochrome 12 - bit packed
	Mono12Packed = 0x010C0006
	#  @brief PFNC Bayer Green - Red 10 - bit unpacked
	BayerGR10 = 0x0110000C
	#  @brief PFNC Bayer Red - Green 10 - bit unpacked
	BayerRG10 = 0x0110000D
	#  @brief PFNC Bayer Green - Blue 10 - bit unpacked
	BayerGB10 = 0x0110000E
	#  @brief PFNC Bayer Blue - Green 10 - bit unpacked
	BayerBG10 = 0x0110000F
	#  @brief PFNC Bayer Green - Red 12 - bit unpacked
	BayerGR12 = 0x01100010
	#  @brief PFNC Bayer Red - Green 12 - bit unpacked
	BayerRG12 = 0x01100011
	#  @brief PFNC Bayer Green - Blue 12 - bit unpacked
	BayerGB12 = 0x01100012
	#  @brief PFNC Bayer Blue - Green 12 - bit unpacked
	BayerBG12 = 0x01100013
	#  @brief PFNC Red - Green - Blue - alpha 8 - bit
	RGBa8 = 0x02200016
	#  @brief PFNC Blue - Green - Red - alpha 8 - bit
	BGRa8 = 0x02200017
	#  @brief PFNC Red - Green - Blue 10 - bit unpacked
	RGB10 = 0x02300018
	#  @brief PFNC Blue - Green - Red 10 - bit unpacked
	BGR10 = 0x02300019
	#  @brief PFNC Red - Green - Blue 12 - bit unpacked
	RGB12 = 0x0230001A
	#  @brief PFNC Blue - Green - Red 12 - bit unpacked
	BGR12 = 0x0230001B
	#  @brief GigE Vision 2.0 Red - Green - Blue 10 - bit packed - variant 1
	RGB10V1Packed = 0x0220001C
	#  @brief PFNC Red - Green - Blue 10 - bit packed into 32 - bit
	RGB10p32 = 0x0220001D
	#  @brief PFNC Red - Green - Blue 8 - bit planar
	RGB8_Planar = 0x02180021
	#  @brief PFNC Red - Green - Blue 10 - bit unpacked planar
	RGB10_Planar = 0x02300022
	#  @brief PFNC Red - Green - Blue 12 - bit unpacked planar
	RGB12_Planar = 0x02300023
	#  @brief PFNC Red - Green - Blue 16 - bit planar
	RGB16_Planar = 0x02300024
	#  @brief GigE Vision 2.0 Bayer Green - Red 10 - bit packed
	BayerGR10Packed = 0x010C0026
	#  @brief GigE Vision 2.0 Bayer Red - Green 10 - bit packed
	BayerRG10Packed = 0x010C0027
	#  @brief GigE Vision 2.0 Bayer Green - Blue 10 - bit packed
	BayerGB10Packed = 0x010C0028
	#  @brief GigE Vision 2.0 Bayer Blue - Green 10 - bit packed
	BayerBG10Packed = 0x010C0029
	#  @brief GigE Vision 2.0 Bayer Green - Red 12 - bit packed
	BayerGR12Packed = 0x010C002A
	#  @brief GigE Vision 2.0 Bayer Red - Green 12 - bit packed
	BayerRG12Packed = 0x010C002B
	#  @brief GigE Vision 2.0 Bayer Green - Blue 12 - bit packed
	BayerGB12Packed = 0x010C002C
	#  @brief GigE Vision 2.0 Bayer Blue - Green 12 - bit packed
	BayerBG12Packed = 0x010C002D
	#  @brief PFNC Bayer Green - Red 16 - bit
	BayerGR16 = 0x0110002E
	#  @brief PFNC Bayer Red - Green 16 - bit
	BayerRG16 = 0x0110002F
	#  @brief PFNC Bayer Green - Blue 16 - bit
	BayerGB16 = 0x01100030
	#  @brief PFNC Bayer Blue - Green 16 - bit
	BayerBG16 = 0x01100031
	#  @brief PFNC Red - Green - Blue 16 - bit
	RGB16 = 0x02300033
	#  @brief GigE Vision 2.0 Red - Green - Blue 12 - bit packed - variant 1
	RGB12V1Packed = 0x02240034
	#  @brief PFNC YCbCr 4:4 : 4 8 - bit
	YCbCr8_CbYCr = 0x0218003A
	#  @brief PFNC YCbCr 4 : 2 : 2 8 - bit
	YCbCr422_8 = 0x0210003B
	#  @brief PFNC YCbCr 4 : 1 : 1 8 - bit
	YCbCr411_8_CbYYCrYY = 0x020C003C
	#  @brief PFNC YCbCr 4 : 4 : 4 8 - bit BT.601
	YCbCr601_8_CbYCr = 0x0218003D
	#  @brief PFNC YCbCr 4 : 2 : 2 8 - bit BT.601
	YCbCr601_422_8 = 0x0210003E
	#  @brief PFNC YCbCr 4 : 1 : 1 8 - bit BT.601
	YCbCr601_411_8_CbYYCrYY = 0x020C003F
	#  @brief PFNC YCbCr 4 : 1 : 1 8 - bit BT.709
	YCbCr709_411_8_CbYYCrYY = 0x020C0042
	#  @brief PFNC YCbCr 4 : 2 : 2 8 - bit
	YCbCr422_8_CbYCrY = 0x02100043
	#  @brief PFNC YCbCr 4 : 2 : 2 8 - bit BT.601
	YCbCr601_422_8_CbYCrY = 0x02100044
	#  @brief PFNC YCbCr 4 : 2 : 2 8 - bit BT.709
	YCbCr709_422_8_CbYCrY = 0x02100045
	#  @brief PFNC Blue - Green - Red 10 - bit packed
	BGR10p = 0x021E0048
	#  @brief PFNC Blue - Green - Red 12 - bit packed
	BGR12p = 0x02240049
	#  @brief PFNC Blue - Green - Red 14 - bit unpacked
	BGR14 = 0x0230004A
	#  @brief PFNC Blue - Green - Red 16 - bit
	BGR16 = 0x0230004B
	#  @brief PFNC Blue - Green - Red - alpha 10 - bit unpacked
	BGRa10 = 0x0240004C
	#  @brief PFNC Blue - Green - Red - alpha 10 - bit packed
	BGRa10p = 0x0228004D
	#  @brief PFNC Blue - Green - Red - alpha 12 - bit unpacked
	BGRa12 = 0x0240004E
	#  @brief PFNC Blue - Green - Red - alpha 12 - bit packed
	BGRa12p = 0x0230004F
	#  @brief PFNC Blue - Green - Red - alpha 14 - bit unpacked
	BGRa14 = 0x02400050
	#  @brief PFNC Blue - Green - Red - alpha 16 - bit
	BGRa16 = 0x02400051
	#  @brief PFNC Bayer Blue - Green 10 - bit packed
	BayerBG10p = 0x010A0052
	#  @brief PFNC Bayer Blue - Green 12 - bit packed
	BayerBG12p = 0x010C0053
	#  @brief PFNC Bayer Green - Blue 10 - bit packed
	BayerGB10p = 0x010A0054
	#  @brief PFNC Bayer Green - Blue 12 - bit packed
	BayerGB12p = 0x010C0055
	#  @brief PFNC Bayer Green - Red 10 - bit packed
	BayerGR10p = 0x010A0056
	#  @brief PFNC Bayer Green - Red 12 - bit packed
	BayerGR12p = 0x010C0057
	#  @brief PFNC Bayer Red - Green 10 - bit packed
	BayerRG10p = 0x010A0058
	#  @brief PFNC Bayer Red - Green 12 - bit packed
	BayerRG12p = 0x010C0059
	#  @brief PFNC YCbCr 4:1 : 1 8 - bit
	YCbCr411_8 = 0x020C005A
	#  @brief PFNC YCbCr 4 : 4 : 4 8 - bit
	YCbCr8 = 0x0218005B
	#  @brief PFNC Red - Green - Blue 10 - bit packed
	RGB10p = 0x021E005C
	#  @brief PFNC Red - Green - Blue 12 - bit packed
	RGB12p = 0x0224005D
	#  @brief PFNC Red - Green - Blue 14 - bit unpacked
	RGB14 = 0x0230005E
	#  @brief PFNC Red - Green - Blue - alpha 10 - bit unpacked
	RGBa10 = 0x0240005F
	#  @brief PFNC Red - Green - Blue - alpha 10 - bit packed
	RGBa10p = 0x02280060
	#  @brief PFNC Red - Green - Blue - alpha 12 - bit unpacked
	RGBa12 = 0x02400061
	#  @brief PFNC Red - Green - Blue - alpha 12 - bit packed
	RGBa12p = 0x02300062
	#  @brief PFNC Red - Green - Blue - alpha 14 - bit unpacked
	RGBa14 = 0x02400063
	#  @brief PFNC Red - Green - Blue - alpha 16 - bit
	RGBa16 = 0x02400064
	#  @brief PFNC YCbCr 4:2 : 2 10 - bit unpacked
	YCbCr422_10 = 0x02200065
	#  @brief PFNC YCbCr 4 : 2 : 2 12 - bit unpacked
	YCbCr422_12 = 0x02200066
	#  @brief PFNC Sparse Color Filter #1 White - Blue - White - Green 8 - bit
	SCF1WBWG8 = 0x01080067
	#  @brief PFNC Sparse Color Filter #1 White - Blue - White - Green 10 - bit unpacked
	SCF1WBWG10 = 0x01100068
	#  @brief PFNC Sparse Color Filter #1 White - Blue - White - Green 10 - bit packed
	SCF1WBWG10p = 0x010A0069
	#  @brief PFNC Sparse Color Filter #1 White - Blue - White - Green 12 - bit unpacked
	SCF1WBWG12 = 0x0110006A
	#  @brief PFNC Sparse Color Filter #1 White - Blue - White - Green 12 - bit packed
	SCF1WBWG12p = 0x010C006B
	#  @brief PFNC Sparse Color Filter #1 White - Blue - White - Green 14 - bit unpacked
	SCF1WBWG14 = 0x0110006C
	#  @brief PFNC Sparse Color Filter #1 White - Blue - White - Green 16 - bit unpacked
	SCF1WBWG16 = 0x0110006D
	#  @brief PFNC Sparse Color Filter #1 White - Green - White - Blue 8 - bit
	SCF1WGWB8 = 0x0108006E
	#  @brief PFNC Sparse Color Filter #1 White - Green - White - Blue 10 - bit unpacked
	SCF1WGWB10 = 0x0110006F
	#  @brief PFNC Sparse Color Filter #1 White - Green - White - Blue 10 - bit packed
	SCF1WGWB10p = 0x010A0070
	#  @brief PFNC Sparse Color Filter #1 White - Green - White - Blue 12 - bit unpacked
	SCF1WGWB12 = 0x01100071
	#  @brief PFNC Sparse Color Filter #1 White - Green - White - Blue 12 - bit packed
	SCF1WGWB12p = 0x010C0072
	#  @brief PFNC Sparse Color Filter #1 White - Green - White - Blue 14 - bit unpacked
	SCF1WGWB14 = 0x01100073
	#  @brief PFNC Sparse Color Filter #1 White - Green - White - Blue 16 - bit
	SCF1WGWB16 = 0x01100074
	#  @brief PFNC Sparse Color Filter #1 White - Green - White - Red 8 - bit
	SCF1WGWR8 = 0x01080075
	#  @brief PFNC Sparse Color Filter #1 White - Green - White - Red 10 - bit unpacked
	SCF1WGWR10 = 0x01100076
	#  @brief PFNC Sparse Color Filter #1 White - Green - White - Red 10 - bit packed
	SCF1WGWR10p = 0x010A0077
	#  @brief PFNC Sparse Color Filter #1 White - Green - White - Red 12 - bit unpacked
	SCF1WGWR12 = 0x01100078
	#  @brief PFNC Sparse Color Filter #1 White - Green - White - Red 12 - bit packed
	SCF1WGWR12p = 0x010C0079
	#  @brief PFNC Sparse Color Filter #1 White - Green - White - Red 14 - bit unpacked
	SCF1WGWR14 = 0x0110007A
	#  @brief PFNC Sparse Color Filter #1 White - Green - White - Red 16 - bit
	SCF1WGWR16 = 0x0110007B
	#  @brief PFNC Sparse Color Filter #1 White - Red - White - Green 8 - bit
	SCF1WRWG8 = 0x0108007C
	#  @brief PFNC Sparse Color Filter #1 White - Red - White - Green 10 - bit unpacked
	SCF1WRWG10 = 0x0110007D
	#  @brief PFNC Sparse Color Filter #1 White - Red - White - Green 10 - bit packed
	SCF1WRWG10p = 0x010A007E
	#  @brief PFNC Sparse Color Filter #1 White - Red - White - Green 12 - bit unpacked
	SCF1WRWG12 = 0x0110007F
	#  @brief PFNC Sparse Color Filter #1 White - Red - White - Green 12 - bit packed
	SCF1WRWG12p = 0x010C0080
	#  @brief PFNC Sparse Color Filter #1 White - Red - White - Green 14 - bit unpacked
	SCF1WRWG14 = 0x01100081
	#  @brief PFNC Sparse Color Filter #1 White - Red - White - Green 16 - bit
	SCF1WRWG16 = 0x01100082
	#  @brief PFNC YCbCr 4:4 : 4 10 - bit unpacked
	YCbCr10_CbYCr = 0x02300083
	#  @brief PFNC YCbCr 4 : 4 : 4 10 - bit packed
	YCbCr10p_CbYCr = 0x021E0084
	#  @brief PFNC YCbCr 4 : 4 : 4 12 - bit unpacked
	YCbCr12_CbYCr = 0x02300085
	#  @brief PFNC YCbCr 4 : 4 : 4 12 - bit packed
	YCbCr12p_CbYCr = 0x02240086
	#  @brief PFNC YCbCr 4 : 2 : 2 10 - bit packed
	YCbCr422_10p = 0x02140087
	#  @brief PFNC YCbCr 4 : 2 : 2 12 - bit packed
	YCbCr422_12p = 0x02180088
	#  @brief PFNC YCbCr 4 : 4 : 4 10 - bit unpacked BT.601
	YCbCr601_10_CbYCr = 0x02300089
	#  @brief PFNC YCbCr 4 : 4 : 4 10 - bit packed BT.601
	YCbCr601_10p_CbYCr = 0x021E008A
	#  @brief PFNC YCbCr 4 : 4 : 4 12 - bit unpacked BT.601
	YCbCr601_12_CbYCr = 0x0230008B
	#  @brief PFNC YCbCr 4 : 4 : 4 12 - bit packed BT.601
	YCbCr601_12p_CbYCr = 0x0224008C
	#  @brief PFNC YCbCr 4 : 2 : 2 10 - bit unpacked BT.601
	YCbCr601_422_10 = 0x0220008D
	#  @brief PFNC YCbCr 4 : 2 : 2 10 - bit packed BT.601
	YCbCr601_422_10p = 0x0214008E
	#  @brief PFNC YCbCr 4 : 2 : 2 12 - bit unpacked BT.601
	YCbCr601_422_12 = 0x0220008F
	#  @brief PFNC YCbCr 4 : 2 : 2 12 - bit packed BT.601
	YCbCr601_422_12p = 0x02180090
	#  @brief PFNC YCbCr 4 : 4 : 4 10 - bit unpacked BT.709
	YCbCr709_10_CbYCr = 0x02300091
	#  @brief PFNC YCbCr 4 : 4 : 4 10 - bit packed BT.709
	YCbCr709_10p_CbYCr = 0x021E0092
	#  @brief PFNC YCbCr 4 : 4 : 4 12 - bit unpacked BT.709
	YCbCr709_12_CbYCr = 0x02300093
	#  @brief PFNC YCbCr 4 : 4 : 4 12 - bit packed BT.709
	YCbCr709_12p_CbYCr = 0x02240094
	#  @brief PFNC YCbCr 4 : 2 : 2 10 - bit unpacked BT.709
	YCbCr709_422_10 = 0x02200095
	#  @brief PFNC YCbCr 4 : 2 : 2 10 - bit packed BT.709
	YCbCr709_422_10p = 0x02140096
	#  @brief PFNC YCbCr 4 : 2 : 2 12 - bit unpacked BT.709
	YCbCr709_422_12 = 0x02200097
	#  @brief PFNC YCbCr 4 : 2 : 2 12 - bit packed BT.709
	YCbCr709_422_12p = 0x02180098
	#  @brief PFNC YCbCr 4 : 2 : 2 10 - bit unpacked
	YCbCr422_10_CbYCrY = 0x02200099
	#  @brief PFNC YCbCr 4 : 2 : 2 10 - bit packed
	YCbCr422_10p_CbYCrY = 0x0214009A
	#  @brief PFNC YCbCr 4 : 2 : 2 12 - bit unpacked
	YCbCr422_12_CbYCrY = 0x0220009B
	#  @brief PFNC YCbCr 4 : 2 : 2 12 - bit packed
	YCbCr422_12p_CbYCrY = 0x0218009C
	#  @brief PFNC YCbCr 4 : 2 : 2 10 - bit unpacked BT.601
	YCbCr601_422_10_CbYCrY = 0x0220009D
	#  @brief PFNC YCbCr 4 : 2 : 2 10 - bit packed BT.601
	YCbCr601_422_10p_CbYCrY = 0x0214009E
	#  @brief PFNC YCbCr 4 : 2 : 2 12 - bit unpacked BT.601
	YCbCr601_422_12_CbYCrY = 0x0220009F
	#  @brief PFNC YCbCr 4 : 2 : 2 12 - bit packed BT.601
	YCbCr601_422_12p_CbYCrY = 0x021800A0
	#  @brief PFNC YCbCr 4 : 2 : 2 10 - bit unpacked BT.709
	YCbCr709_422_10_CbYCrY = 0x022000A1
	#  @brief PFNC YCbCr 4 : 2 : 2 10 - bit packed BT.709
	YCbCr709_422_10p_CbYCrY = 0x021400A2
	#  @brief PFNC YCbCr 4 : 2 : 2 12 - bit unpacked BT.709
	YCbCr709_422_12_CbYCrY = 0x022000A3
	#  @brief PFNC YCbCr 4 : 2 : 2 12 - bit packed BT.709
	YCbCr709_422_12p_CbYCrY = 0x021800A4
	#  @brief PFNC Bi - color Red / Green - Blue / Green 8 - bit
	BiColorRGBG8 = 0x021000A5
	#  @brief PFNC Bi - color Blue / Green - Red / Green 8 - bit
	BiColorBGRG8 = 0x021000A6
	#  @brief PFNC Bi - color Red / Green - Blue / Green 10 - bit unpacked
	BiColorRGBG10 = 0x022000A7
	#  @brief PFNC Bi - color Red / Green - Blue / Green 10 - bit packed
	BiColorRGBG10p = 0x021400A8
	#  @brief PFNC Bi - color Blue / Green - Red / Green 10 - bit unpacked
	BiColorBGRG10 = 0x022000A9
	#  @brief PFNC Bi - color Blue / Green - Red / Green 10 - bit packed
	BiColorBGRG10p = 0x021400AA
	#  @brief PFNC Bi - color Red / Green - Blue / Green 12 - bit unpacked
	BiColorRGBG12 = 0x022000AB
	#  @brief PFNC Bi - color Red / Green - Blue / Green 12 - bit packed
	BiColorRGBG12p = 0x021800AC
	#  @brief PFNC Bi - color Blue / Green - Red / Green 12 - bit unpacked
	BiColorBGRG12 = 0x022000AD
	#  @brief PFNC Bi - color Blue / Green - Red / Green 12 - bit packed
	BiColorBGRG12p = 0x021800AE
	#  @brief PFNC 3D coordinate A 8 - bit
	Coord3D_A8 = 0x010800AF
	#  @brief PFNC 3D coordinate B 8 - bit
	Coord3D_B8 = 0x010800B0
	#  @brief PFNC 3D coordinate C 8 - bit
	Coord3D_C8 = 0x010800B1
	#  @brief PFNC 3D coordinate A - B - C 8 - bit
	Coord3D_ABC8 = 0x021800B2
	#  @brief PFNC 3D coordinate A - B - C 8 - bit planar
	Coord3D_ABC8_Planar = 0x021800B3
	#  @brief PFNC 3D coordinate A - C 8 - bit
	Coord3D_AC8 = 0x021000B4
	#  @brief PFNC 3D coordinate A - C 8 - bit planar
	Coord3D_AC8_Planar = 0x021000B5
	#  @brief PFNC 3D coordinate A 16 - bit
	Coord3D_A16 = 0x011000B6
	#  @brief PFNC 3D coordinate B 16 - bit
	Coord3D_B16 = 0x011000B7
	#  @brief PFNC 3D coordinate C 16 - bit
	Coord3D_C16 = 0x011000B8
	#  @brief PFNC 3D coordinate A - B - C 16 - bit
	Coord3D_ABC16 = 0x023000B9
	#  @brief PFNC 3D coordinate A - B - C 16 - bit planar
	Coord3D_ABC16_Planar = 0x023000BA
	#  @brief PFNC 3D coordinate A - C 16 - bit
	Coord3D_AC16 = 0x022000BB
	#  @brief PFNC 3D coordinate A - C 16 - bit planar
	Coord3D_AC16_Planar = 0x022000BC
	#  @brief PFNC 3D coordinate A 32 - bit floating point
	Coord3D_A32f = 0x012000BD
	#  @brief PFNC 3D coordinate B 32 - bit floating point
	Coord3D_B32f = 0x012000BE
	#  @brief PFNC 3D coordinate C 32 - bit floating point
	Coord3D_C32f = 0x012000BF
	#  @brief PFNC 3D coordinate A - B - C 32 - bit floating point
	Coord3D_ABC32f = 0x026000C0
	#  @brief PFNC 3D coordinate A - B - C 32 - bit floating point planar
	Coord3D_ABC32f_Planar = 0x026000C1
	#  @brief PFNC 3D coordinate A - C 32 - bit floating point
	Coord3D_AC32f = 0x024000C2
	#  @brief PFNC 3D coordinate A - C 32 - bit floating point planar
	Coord3D_AC32f_Planar = 0x024000C3
	#  @brief PFNC Confidence 1 - bit unpacked
	Confidence1 = 0x010800C4
	#  @brief PFNC Confidence 1 - bit packed
	Confidence1p = 0x010100C5
	#  @brief PFNC Confidence 8 - bit
	Confidence8 = 0x010800C6
	#  @brief PFNC Confidence 16 - bit
	Confidence16 = 0x011000C7
	#  @brief PFNC Confidence 32 - bit floating point
	Confidence32f = 0x012000C8
	#  @brief PFNC Red 8 - bit
	R8 = 0x010800C9
	#  @brief PFNC Red 10 - bit
	R10 = 0x010A00CA
	#  @brief PFNC Red 12 - bit
	R12 = 0x010C00CB
	#  @brief PFNC Red 16 - bit
	R16 = 0x011000CC
	#  @brief PFNC Green 8 - bit
	G8 = 0x010800CD
	#  @brief PFNC Green 10 - bit
	G10 = 0x010A00CE
	#  @brief PFNC Green 12 - bit
	G12 = 0x010C00CF
	#  @brief PFNC Green 16 - bit
	G16 = 0x011000D0
	#  @brief PFNC Blue 8 - bit
	B8 = 0x010800D1
	#  @brief PFNC Blue 10 - bit
	B10 = 0x010A00D2
	#  @brief PFNC Blue 12 - bit
	B12 = 0x010C00D3
	#  @brief PFNC Blue 16 - bit
	B16 = 0x011000D4
	#  @brief PFNC 3D coordinate A 10 - bit packed
	Coord3D_A10p = 0x010A00D5
	#  @brief PFNC 3D coordinate B 10 - bit packed
	Coord3D_B10p = 0x010A00D6
	#  @brief PFNC 3D coordinate C 10 - bit packed
	Coord3D_C10p = 0x010A00D7
	#  @brief PFNC 3D coordinate A 12 - bit packed
	Coord3D_A12p = 0x010C00D8
	#  @brief PFNC 3D coordinate B 12 - bit packed
	Coord3D_B12p = 0x010C00D9
	#  @brief PFNC 3D coordinate C 12 - bit packed
	Coord3D_C12p = 0x010C00DA
	#  @brief PFNC 3D coordinate A - B - C 10 - bit packed
	Coord3D_ABC10p = 0x021E00DB
	#  @brief PFNC 3D coordinate A - B - C 10 - bit packed planar
	Coord3D_ABC10p_Planar = 0x021E00DC
	#  @brief PFNC 3D coordinate A - B - C 12 - bit packed
	Coord3D_ABC12p = 0x022400DE
	#  @brief PFNC 3D coordinate A - B - C 12 - bit packed planar
	Coord3D_ABC12p_Planar = 0x022400DF
	#  @brief PFNC 3D coordinate A - C 10 - bit packed
	Coord3D_AC10p = 0x021400F0
	#  @brief PFNC 3D coordinate A - C 10 - bit packed planar
	Coord3D_AC10p_Planar = 0x021400F1
	#  @brief PFNC 3D coordinate A - C 12 - bit packed
	Coord3D_AC12p = 0x021800F2
	#  @brief PFNC 3D coordinate A - C 12 - bit packed planar
	Coord3D_AC12p_Planar = 0x021800F3
	#  @brief PFNC YCbCr 4:4 : 4 8 - bit BT.2020
	YCbCr2020_8_CbYCr = 0x021800F4
	#  @brief PFNC YCbCr 4 : 4 : 4 10 - bit unpacked BT.2020
	YCbCr2020_10_CbYCr = 0x023000F5
	#  @brief PFNC YCbCr 4 : 4 : 4 10 - bit packed BT.2020
	YCbCr2020_10p_CbYCr = 0x021E00F6
	#  @brief PFNC YCbCr 4 : 4 : 4 12 - bit unpacked BT.2020
	YCbCr2020_12_CbYCr = 0x023000F7
	#  @brief PFNC YCbCr 4 : 4 : 4 12 - bit packed BT.2020
	YCbCr2020_12p_CbYCr = 0x022400F8
	#  @brief PFNC YCbCr 4 : 1 : 1 8 - bit BT.2020
	YCbCr2020_411_8_CbYYCrYY = 0x020C00F9
	#  @brief PFNC YCbCr 4 : 2 : 2 8 - bit BT.2020
	YCbCr2020_422_8 = 0x021000FA
	#  @brief PFNC YCbCr 4 : 2 : 2 8 - bit BT.2020
	YCbCr2020_422_8_CbYCrY = 0x021000FB
	#  @brief PFNC YCbCr 4 : 2 : 2 10 - bit unpacked BT.2020
	YCbCr2020_422_10 = 0x022000FC
	#  @brief PFNC YCbCr 4 : 2 : 2 10 - bit unpacked BT.2020
	YCbCr2020_422_10_CbYCrY = 0x022000FD
	#  @brief PFNC YCbCr 4 : 2 : 2 10 - bit packed BT.2020
	YCbCr2020_422_10p = 0x021400FE
	#  @brief PFNC YCbCr 4 : 2 : 2 10 - bit packed BT.2020
	YCbCr2020_422_10p_CbYCrY = 0x021400FF
	#  @brief PFNC YCbCr 4 : 2 : 2 12 - bit unpacked BT.2020
	YCbCr2020_422_12 = 0x02200100
	#  @brief PFNC YCbCr 4 : 2 : 2 12 - bit unpacked BT.2020
	YCbCr2020_422_12_CbYCrY = 0x02200101
	#  @brief PFNC YCbCr 4 : 2 : 2 12 - bit packed BT.2020
	YCbCr2020_422_12p = 0x02180102
	#  @brief PFNC YCbCr 4 : 2 : 2 12 - bit packed BT.2020
	YCbCr2020_422_12p_CbYCrY = 0x02180103
	#  @brief PFNC Monochrome 14 - bit packed
	Mono14p = 0x010E0104
	#  @brief PFNC Bayer Green - Red 14 - bit packed
	BayerGR14p = 0x010E0105
	#  @brief PFNC Bayer Red - Green 14 - bit packed
	BayerRG14p = 0x010E0106
	#  @brief PFNC Bayer Green - Blue 14 - bit packed
	BayerGB14p = 0x010E0107
	#  @brief PFNC Bayer Blue - Green 14 - bit packed
	BayerBG14p = 0x010E0108
	#  @brief PFNC Bayer Green - Red 14 - bit
	BayerGR14 = 0x01100109
	#  @brief PFNC Bayer Red - Green 14 - bit
	BayerRG14 = 0x0110010A
	#  @brief PFNC Bayer Green - Blue 14 - bit
	BayerGB14 = 0x0110010B
	#  @brief PFNC Bayer Blue - Green 14 - bit
	BayerBG14 = 0x0110010C
	#  @brief PFNC Bayer Green - Red 4 - bit packed
	BayerGR4p = 0x0104010D
	#  @brief PFNC Bayer Red - Green 4 - bit packed
	BayerRG4p = 0x0104010E
	#  @brief PFNC Bayer Green - Blue 4 - bit packed
	BayerGB4p = 0x0104010F
	#  @brief PFNC Bayer Blue - Green 4 - bit packed
	BayerBG4p = 0x01040110

## @~chinese
#  @brief Payloadģʽ
#  @~english
#  @brief Payload mode
class SciCamPayloadMode(IntEnum):
	## @~chinese
	#  @brief δ֪
	#  @~english
	#  @brief Unknown
	SciCam_PayloadMode_Unknown = 0
	## @~chinese
	#  @brief 2D
	#  @~english
	#  @brief 2D
	SciCam_PayloadMode_2D = 1
	## @~chinese
	#  @brief LP3Dͼ��
	#  @~english
	#  @brief Image
	SciCam_PayloadMode_LP3D_Image = 11
	## @~chinese
	#  @brief LP3D����
	#  @~english
	#  @brief Contour
	SciCam_PayloadMode_LP3D_Contour = 12
	## @~chinese
	#  @brief LP3D���ͼ
	#  @~english
	#  @brief Batch Contour
	SciCam_PayloadMode_LP3D_BatchContour = 13
	## @~chinese
	#  @brief �������
	#  @~english
	#  @brief ACC
	SciCam_PayloadMode_ACC = 21

## @~chinese
#  @brief Payload��������
#  @~english
#  @brief Payload data type
class SciCamPayloadDataType(IntEnum):
	#  @brief 8U
	SciCam_Payload_DataType_UCHAR = 0
	#  @brief 8S
	SciCam_Payload_DataType_CHAR = 1
	#  @brief 16U
	SciCam_Payload_DataType_USHORT = 2
	#  @brief 16S
	SciCam_Payload_DataType_SHORT = 3
	#  @brief 32S
	SciCam_Payload_DataType_INT = 4
	#  @brief 32F
	SciCam_Payload_DataType_FLOAT = 5
	#  @brief 64F
	SciCam_Payload_DataType_DOUBLE = 6

## @~chinese
#  @brief ���ͼ������
#  @details ����ͼ��Ŀ��ȡ��߶ȡ�ƫ�������������͵���Ϣ
#  @param width ͼ�����
#  @param height ͼ��߶�
#  @param offsetX Xƫ����
#  @param offsetY Yƫ����
#  @param paddingX X��Ե���
#  @param paddingY Y��Ե���
#  @param pixelType ��������
#  @param reserve Ԥ����չ
#  @~english
#  @brief Camera image attribute
#  @details Contains image width, height, offset, pixel type, etc.
#  @param width Image width
#  @param height Image height
#  @param offsetX X offset
#  @param offsetY Y offset
#  @param paddingX X padding
#  @param paddingY Y padding
#  @param pixelType Pixel type
#  @param reserve Reserved extension
class _SCI_CAM_IMAGE_ATTRIBUTE_(ctypes.Structure):
	_fields_ = [
		("width", ctypes.c_uint64),
		("height", ctypes.c_uint64),
		("offsetX", ctypes.c_uint64),
		("offsetY", ctypes.c_uint64),
		("paddingX", ctypes.c_uint64),
		("paddingY", ctypes.c_uint64),
		("pixelType", ctypes.c_int),
		("reserve", ctypes.c_ubyte * 32)]

## @~chinese
#  @brief ���ͼ������
#  @~english
#  @brief Camera image attribute
SCI_CAM_IMAGE_ATTRIBUTE = _SCI_CAM_IMAGE_ATTRIBUTE_
## @~chinese
#  @brief ���ͼ������ָ��
#  @~english
#  @brief Camera image attribute pointer
PSCI_CAM_IMAGE_ATTRIBUTE = ctypes.POINTER(_SCI_CAM_IMAGE_ATTRIBUTE_)

## @~chinese
#  @brief Payload����
#  @details ����֡ID��֡���������ԡ���ChunkData��ʱ�����Payloadģʽ��ͼ�����ԡ�Ԥ����չ����Ϣ
#  @param frameID ֡ID
#  @param isComplete ֡����������
#  @param hasChunk ��ChunkData
#  @param timeStamp ʱ���
#  @param payloadMode Payloadģʽ
#  @param imgAttr ͼ������
#  @param reserve Ԥ����չ
#  @~english
#  @brief Payload attribute
#  @details Contains frame ID, frame data integrity, chunk data, time stamp, payload mode, image attribute, and reserved extension
#  @param frameID Frame ID
#  @param isComplete Frame data integrity
#  @param hasChunk Has chunk data
#  @param timeStamp Time stamp
#  @param payloadMode Payload mode
#  @param imgAttr Image attribute
#  @param reserve Reserved extension
class _SCI_CAM_PAYLOAD_ATTRIBUTE_(ctypes.Structure):
	_fields_ = [
		("frameID", ctypes.c_uint64),
		("isComplete", ctypes.c_bool),
		("hasChunk", ctypes.c_bool),
		("timeStamp", ctypes.c_uint64),
		("payloadMode", ctypes.c_int),
		("imgAttr", SCI_CAM_IMAGE_ATTRIBUTE),
		("reserve", ctypes.c_ubyte * 64)]

## @~chinese
#  @brief Payload����
#  @~english
#  @brief Payload attribute
SCI_CAM_PAYLOAD_ATTRIBUTE = _SCI_CAM_PAYLOAD_ATTRIBUTE_
## @~chinese
#  @brief Payload����ָ��
#  @~english
#  @brief Payload attribute pointer
PSCI_CAM_PAYLOAD_ATTRIBUTE = ctypes.POINTER(_SCI_CAM_PAYLOAD_ATTRIBUTE_)

## @~chinese
#  @brief Chunk data�ṹ
#  @details ����ID�����ȡ�ָ��chunk data�ڴ�ͷָ�����Ϣ
#  @param id ID
#  @param len ����
#  @param data ָ��chunk data�ڴ�ͷָ��
#  @~english
#  @brief Chunk data structure
#  @details Contains ID, length, and pointer to the head of chunk data memory
#  @param id ID
#  @param len Length
#  @param data Pointer to the head of chunk data memory
class _SCI_CAM_CHUNK_(ctypes.Structure):
	_fields_ = [
		("id", ctypes.c_uint64),
		("len", ctypes.c_uint64),
		("data", ctypes.c_void_p)]
SCI_CAM_CHUNK = _SCI_CAM_CHUNK_
PSCI_CAM_CHUNK = ctypes.POINTER(_SCI_CAM_CHUNK_)

## @~chinese
#  @brief Chunk data�б�
#  @details ������Ч������Chunk data����
#  @param count ��Ч����
#  @param chunk Chunk data����
#  @~english
#  @brief Chunk data list
#  @details Contains the number of valid chunks and an array of chunk data
#  @param count Number of valid chunks
#  @param chunk Array of chunk data
class _SCI_CAM_CHUNK_LIST_(ctypes.Structure):
	_fields_ = [
		("count", ctypes.c_uint),
		("chunk", SCI_CAM_CHUNK * 256)]

## @~chinese
#  @brief Chunk data�б�
#  @~english
#  @brief Chunk data list
SCI_CAM_CHUNK_LIST = _SCI_CAM_CHUNK_LIST_
## @~chinese
#  @brief Chunk data�б�ָ��
#  @~english
#  @brief Chunk data list pointer
PSCI_CAM_CHUNK_LIST = ctypes.POINTER(_SCI_CAM_CHUNK_LIST_)

## @~chinese
#  @brief Chunk Ԫ������Ϣ��3D��ɨ���������豸ר����
#  @details �����汾�š�֡ID��֡��������֡����������Ϣ
#  @param version �汾��
#  @param frameId ֡ID
#  @param index ֡������
#  @param finished ֡������
#  @~english
#  @brief Metadata Information(Exclusive to 3D Line Scan Laser Profiling Devices)
#  @details Contains version number, frame ID, intra-frame index, and frame completion flag
#  @param version Version number
#  @param frameId Frame ID
#  @param index Intra-frame index
#  @param finished Frame completion flag
class _SCI_CAM_LP3D_META_(ctypes.Structure):
	_fields_ = [
		("version", ctypes.c_uint16),
		("frameId", ctypes.c_uint64),
		("index", ctypes.c_uint32),
		("finished", ctypes.c_bool)]
## @~chinese
#  @brief Chunk data�б�
#  @~english
#  @brief Chunk data list
SCI_CAM_LP3D_META = _SCI_CAM_LP3D_META_
## @~chinese
#  @brief Chunk data�б�ָ��
#  @~english
#  @brief Chunk data list pointer
PSCI_CAM_LP3D_META = ctypes.POINTER(_SCI_CAM_LP3D_META_)

## @~chinese
#  @brief �ṹ���豸���ͣ�3D�ṹ���豸ר����
#  @~english
#  @brief Structured Light Device Type (Exclusive to 3D Structured Light Devices)
class SciCamPayloadSL3DDeviceType(IntEnum):
	## @~chinese
	#  @brief δ֪�豸����
	#  @~english
	#  @brief Unknown device type
	SciCam_payload_SL_DeviceType_Unknown = 0,
	## @~chinese
	#  @brief �����豸����
	#  @~english
	#  @brief Striped device type
	SciCam_payload_SL_DeviceType_Striped = 2,
	## @~chinese
	#  @brief ɢ���豸����
	#  @~english
	#  @brief Speckle device type
	SciCam_payload_SL_DeviceType_Speckle = 3,

## @~chinese
#  @brief SL3DԪ������Ϣ��3D�ṹ���豸ר����
#  @details �����豸���͡��汾�š�֡ID���Ƿ����֡���ݡ������ֵ���Ϣ
#  @param deviceType �豸����
#  @param version �汾��
#  @param frameId ֡ID
#  @param finished �Ƿ����֡����
#  @param reserve ������
#  @~english
#  @brief SL3D Metadata Information (Exclusive to 3D Structured Light Devices)
#  @details Contains device type, version number, frame ID, whether the frame data is finished, and reserved information
#  @param deviceType Device type
#  @param version Version number
#  @param frameId Frame ID
#  @param finished Whether the frame data is finished
#  @param reserve Reserved information
class _SCI_CAM_SL3D_META_(ctypes.Structure):
	_fields_ = [
		("deviceType", ctypes.c_int),
		("version", ctypes.c_short),
		("frameId", ctypes.c_uint32),
		("finished", ctypes.c_bool),
		("reserve", ctypes.c_ubyte * 15)]

## @~chinese
#  @brief SL3DԪ������Ϣ
#  @~english
#  @brief SL3D Metadata Information
SCI_CAM_SL3D_META = _SCI_CAM_SL3D_META_
## @~chinese
#  @brief SL3DԪ������Ϣָ��
#  @~english
#  @brief SL3D Metadata Information Pointer
PSCI_CAM_SL3D_META = ctypes.POINTER(_SCI_CAM_SL3D_META_)

## @~chinese
#  @brief Ŀ���������ͣ�3D�ṹ���豸ר����
#  @~english
#  @brief SL3D Target Data Type (Exclusive to 3D Structured Light Devices)
class SciCamPayloadSL3DTargetDataType(IntEnum):
	## @~chinese
	#  @brief һ�βɼ�����ԭͼ
	#  @~english
	#  @brief All original images collected once
	SciCam_payload_SL_2D = 0
	## @~chinese
	#  @brief ���ƽṹ��3D��������
	#  @~english
	#  @brief 3D point cloud data of striped structured light
	SciCam_payload_SL_Striped_3D = 10
	## @~chinese
	#  @brief ���ƽṹ����2Dԭͼ
	#  @~english
	#  @brief Left 2D original image of striped structured light
	SciCam_payload_SL_Striped_2D_Left = 11
	## @~chinese
	#  @brief ���ƽṹ����2Dԭͼ
	#  @~english
	#  @brief Right 2D original image of striped structured light
	SciCam_payload_SL_Striped_2D_Right = 12
	## @~chinese
	#  @brief ���ƽṹ����2D����ͼ
	#  @~english
	#  @brief Left 2D modulation image of striped structured light
	SciCam_payload_SL_Striped_2D_LeftModulation = 13
	## @~chinese
	#  @brief ���ƽṹ����2D����ͼ
	#  @~english
	#  @brief Right 2D modulation image of striped structured light
	SciCam_payload_SL_Striped_2D_RightModulation = 14
	## @~chinese
	#  @brief ���ƽṹ����2D���ƶԱ�ͼ
	#  @~english
	#  @brief Left 2D modulation contrast image of striped structured light
	SciCam_payload_SL_Striped_2D_LeftModulationContrast = 15
	## @~chinese
	#  @brief ���ƽṹ����2D���ƶԱ�ͼ
	#  @~english
	#  @brief Right 2D modulation contrast image of striped structured light
	SciCam_payload_SL_Striped_2D_RightModulationContrast = 16
	## @~chinese
	#  @brief ���ƽṹ����2D����ͼ
	#  @~english
	#  @brief Left 2D stripe image of striped structured light
	SciCam_payload_SL_Striped_2D_LeftStripe = 17
	## @~chinese
	#  @brief ���ƽṹ����2D����ͼ
	#  @~english
	#  @brief Right 2D stripe image of striped structured light
	SciCam_payload_SL_Striped_2D_RightStripe = 18
	## @~chinese
	#  @brief ɢ�߽ṹ��3D��������
	#  @~english
	#  @brief 3D point cloud data of speckle structured light
	SciCam_payload_SL_Speckle_3D = 40
	## @~chinese
	#  @brief ɢ�߽ṹ����2Dԭͼ
	#  @~english
	#  @brief Left 2D original image of speckle structured light
	SciCam_payload_SL_Speckle_2D_Left = 41
	## @~chinese
	#  @brief ɢ�߽ṹ����2Dԭͼ
	#  @~english
	#  @brief Right 2D original image of speckle structured light
	SciCam_payload_SL_Speckle_2D_Right = 42
	## @~chinese
	#  @brief ɢ�߽ṹ����2D����У��ͼ
	#  @~english
	#  @brief Left 2D epipolar rectification image of speckle structured light
	SciCam_payload_SL_Speckle_2D_LeftEpipolarRectification = 43
	## @~chinese
	#  @brief ɢ�߽ṹ����2D����У��ͼ
	#  @~english
	#  @brief Right 2D epipolar rectification image of speckle structured light
	SciCam_payload_SL_Speckle_2D_RightEpipolarRectification = 44
	## @~chinese
	#  @brief ɢ�߽ṹ��2D��ɫͼ
	#  @~english
	#  @brief 2D color image of speckle structured light
	SciCam_payload_SL_Speckle_2D_Color = 45

## @~chinese
#  @brief 3Dͼ����Ϣ��3D�ṹ���豸ר����
#  @details ������Сֵ�����ֵ���ֱ��ʡ�ƫ�ơ�ģ�����͡������ֵ���Ϣ
#  @param minValue ��Сֵ
#  @param maxValue ���ֵ
#  @param resolutionX X����ֱ���
#  @param resolutionY Y����ֱ���
#  @param resolutionZ Z����ֱ���
#  @param offsetX X����ƫ��
#  @param offsetY Y����ƫ��
#  @param offsetZ Z����ƫ��
#  @param modelType ģ������
#  @param reserve ������
#  @~english
#  @brief 3D Image Information (Exclusive to 3D Structured Light Devices)
#  @details Contains minimum value, maximum value, resolution, offset, model type, and reserved information
#  @param minValue Minimum value
#  @param maxValue Maximum value
#  @param resolutionX X direction resolution
#  @param resolutionY Y direction resolution
#  @param resolutionZ Z direction resolution
#  @param offsetX X direction offset
#  @param offsetY Y direction offset
#  @param offsetZ Z direction offset
#  @param modelType Model type
#  @param reserve Reserved information
class _SCI_CAM_SL3D_3DDATA_INFO_(ctypes.Structure):
	_fields_ = [
		("minValue", ctypes.c_double),
		("maxValue", ctypes.c_double),
		("resolutionX", ctypes.c_double),
		("resolutionY", ctypes.c_double),
		("resolutionZ", ctypes.c_double),
		("offsetX", ctypes.c_double),
		("offsetY", ctypes.c_double),
		("offsetZ", ctypes.c_double),
		("modelType", ctypes.c_ubyte),
		("reserve", ctypes.c_ubyte * 63)]

## @~chinese
#  @brief 3Dͼ����Ϣ
#  @~english
#  @brief 3D Image Information
SCI_CAM_SL3D_3DDATA_INFO = _SCI_CAM_SL3D_3DDATA_INFO_
## @~chinese
#  @brief 3Dͼ����Ϣָ��
#  @~english
#  @brief 3D Image Information Pointer
PSCI_CAM_SL3D_3DDATA_INFO = ctypes.POINTER(_SCI_CAM_SL3D_3DDATA_INFO_)

## @~chinese
#  @brief Ŀ�����ݽṹ��3D�ṹ���豸ר����
#  @details �����豸���͡�ͼ�����͡�ͼ���������Ƿ��Ѿ���������ݡ����ظ�ʽ��ͼ����ȡ�ͼ��߶ȡ�ͼ�񲽳���ͼ��ͨ�������������͡�3D������Ϣ����Ϣ
#  @param deviceType �豸���ͣ��ο��� @ref SciCamPayloadSL3DDeviceType "SciCamPayloadSL3DDeviceType"
#  @param imageType ͼ�����ͣ��ο��� @ref SciCamPayloadSL3DTargetDataType "SciCamPayloadSL3DTargetDataType"
#  @param imageNum ͼ������
#  @param calculated �Ƿ��Ѿ���������ݣ�0��δ���㣬1���Ѽ���
#  @param pixelFormat ���ظ�ʽ���ο��� @ref SciCamPixelType "SciCamPixelType"
#  @param width ͼ�����
#  @param height ͼ��߶�
#  @param step ͼ�񲽳�
#  @param channel ͼ��ͨ����
#  @param dataType �������ͣ��ο��� @ref SciCamPayloadDataType "SciCamPayloadDataType"
#  @param RangeImageInfo 3D������Ϣ������imageTypeΪ @ref SciCam_payload_SL_Striped_3D "SciCam_payload_SL_Striped_3D" �� @ref SciCam_payload_SL_Speckle_3D "SciCam_payload_SL_Speckle_3D" ʱ��Ч
#  @param data ָ��Ŀ������ͷָ��
#  @~english
#  @brief SL3D Target Data Struct (Exclusive to 3D Structured Light Devices)
#  @param deviceType Device type, references: @ref SciCamPayloadSL3DDeviceType "SciCamPayloadSL3DDeviceType"
#  @param imageType Image type, references: @ref SciCamPayloadSL3DTargetDataType "SciCamPayloadSL3DTargetDataType"
#  @param imageNum Image number
#  @param calculated Whether the data has been calculated, 0: not calculated, 1: calculated
#  @param pixelFormat Pixel format, references: @ref SciCamPixelType "SciCamPixelType"
#  @param width Image width
#  @param height Image height
#  @param step Image step
#  @param channel Image channel number
#  @param dataType Data type, references: @ref SciCamPayloadDataType "SciCamPayloadDataType"
#  @param RangeImageInfo 3D data information, valid only when imageType is @ref SciCam_payload_SL_Striped_3D "SciCam_payload_SL_Striped_3D" or @ref SciCam_payload_SL_Speckle_3D "SciCam_payload_SL_Speckle_3D"
#  @param data Pointer to the head of target data
class _SCI_CAM_SL3D_DATA_(ctypes.Structure):
	_fields_ = [
		("deviceType", ctypes.c_int),
		("imageType", ctypes.c_int),
		("imageNum", ctypes.c_ubyte),
		("calculated", ctypes.c_ubyte),
		("pixelFormat", ctypes.c_int),
		("width", ctypes.c_uint32),
		("height", ctypes.c_uint32),
		("step", ctypes.c_uint32),
		("channel", ctypes.c_ushort),
		("dataType", ctypes.c_int),
		("RangeImageInfo", SCI_CAM_SL3D_3DDATA_INFO),
		("data", ctypes.c_void_p)]

## @~chinese
#  @brief 3Dͼ����Ϣ
#  @~english
#  @brief 3D Image Information
SCI_CAM_SL3D_DATA = _SCI_CAM_SL3D_DATA_
## @~chinese
#  @brief 3Dͼ����Ϣָ��
#  @~english
#  @brief 3D Image Information Pointer
PSCI_CAM_SL3D_DATA = ctypes.POINTER(_SCI_CAM_SL3D_DATA_)

## @~chinese
#  @brief ¼���ʽ
#  @~english
#  @brief Record format
class SciRecordFormatType(IntEnum):
	## @~chinese
	#  @brief δ����
	#  @~english
	#  @brief Undefined
	SciRecordFormatType_Undefined = 0
	## @~chinese
	#  @brief AVI��ʽ
	#  @~english
	#  @brief AVI format
	SciRecordFormatType_AVI = 1

## @~chinese
#  @brief ¼����Ϣ
#  @details �����������͡����ȡ��߶ȡ�֡�ʡ�ѹ��������¼���ʽ���ļ�·������Ϣ
#  @param pixelType �������ͣ��ο��� @ref SciCamPixelType "SciCamPixelType"
#  @param width ����
#  @param height �߶�
#  @param frameRate ֡��
#  @param quality ѹ������
#  @param formatType ¼���ʽ���ο��� @ref SciRecordFormatType "SciRecordFormatType"
#  @param strFilePath �ļ�·��
#  @~english
#  @brief Record information
#  @param pixelType Pixel type, references: @ref SciCamPixelType "SciCamPixelType"
#  @param width Width
#  @param height Height
#  @param frameRate Frame rate
#  @param quality Compression quality
#  @param formatType Record format, references: @ref SciRecordFormatType "SciRecordFormatType"
#  @param strFilePath File path
class _SCI_RECORD_INFO_(ctypes.Structure):
	_fields_ = [
		('pixelType', ctypes.c_int),
		('width', ctypes.c_uint),
		('height', ctypes.c_uint),
		('frameRate', ctypes.c_float),
		('quality', ctypes.c_uint),
		('formatType', ctypes.c_int),
		('strFilePath', ctypes.c_char_p)
	]

## @~chinese
#  @brief ¼����Ϣ
#  @~english
#  @brief Record information
SCI_RECORD_INFO = _SCI_RECORD_INFO_
## @~chinese
#  @brief ¼����Ϣָ��
#  @~english
#  @brief Record information pointer
PSCI_RECORD_INFO = ctypes.POINTER(_SCI_RECORD_INFO_)

## @~chinese
#  @brief Ŀ�����ݽṹ���������ר����
#  @details �����Ҷȼ������߼�����blob������blob��������Ϣ
#  @param grayCount �Ҷȼ���
#  @param lineCount �߼���
#  @param blobNumber blob����
#  @param blobCount blob����
#  @~english
#  @brief Target data structure (exclusive to acceleration camera)
#  @param grayCount Gray count
#  @param lineCount Line count
#  @param blobNumber Blob number
#  @param blobCount Blob count
class _SCI_CAM_ACC_BLOB_META_(ctypes.Structure):
	_fields_ = [
		("grayCount", ctypes.c_uint32),
		("lineCount", ctypes.c_uint32),
		("blobNumber", ctypes.c_uint32),
		("blobCount", ctypes.c_uint32 * 256)]
SCI_CAM_ACC_BLOB_META = _SCI_CAM_ACC_BLOB_META_
PSCI_CAM_ACC_BLOB_META = ctypes.POINTER(_SCI_CAM_ACC_BLOB_META_)

## @ingroup module_PayloadParsingInterface_Generic
#  @~chinese
#  @brief ��ȡpayload��������
#  @param payload	[IN]  ָ��payload����ͷָ��
#  @param pAttr		[OUT] ��ȡ����payload�������ԣ���ϸ�ο��� @ref PSCI_CAM_PAYLOAD_ATTRIBUTE "PSCI_CAM_PAYLOAD_ATTRIBUTE"
#  @retval �ɹ��� @ref SCI_CAMERA_OK "SCI_CAMERA_OK"(0)
#  @retval �����μ�: @ref SciCamErrorDefine.h "״̬��"
#  @remarks NULL
#  @~english
#  @brief Get payload data attribute
#  @param payload	[IN]  Pointer to the head of payload data
#  @param pAttr		[OUT] Attributes of the obtained payload data, references: @ref PSCI_CAM_PAYLOAD_ATTRIBUTE "PSCI_CAM_PAYLOAD_ATTRIBUTE"
#  @retval Success: @ref SCI_CAMERA_OK "SCI_CAMERA_OK"
#  @retval Other references: @ref SciCamErrorDefine.h "Error Code List"
#  @remarks NULL
def SciCam_Payload_GetAttribute(payload, pAttr):
	SciCamCtrlDll.SciCam_Payload_GetAttribute.argtypes = (ctypes.c_void_p, PSCI_CAM_PAYLOAD_ATTRIBUTE)
	SciCamCtrlDll.SciCam_Payload_GetAttribute.restype = ctypes.c_uint
	return SciCamCtrlDll.SciCam_Payload_GetAttribute(payload, ctypes.byref(pAttr))

## @ingroup module_PayloadParsingInterface_Generic
#  @~chinese
#  @brief ��ȡͼ������
#  @param payload		[IN]  ָ��payload����ͷָ��
#  @param pImg			[OUT] ��ȡ����ָ��ͼ�������ڴ�ͷָ��
#  @retval �ɹ��� @ref SCI_CAMERA_OK "SCI_CAMERA_OK"(0)
#  @retval �����μ�: @ref SciCamErrorDefine.h "״̬��"
#  @remarks �����ͼ�������ڴ���SDK���䣬��payload���ٶ�����
#  @~english
#  @brief Get image data
#  @param payload		[IN]  Pointer to the head of payload data
#  @param pImg			[OUT] The obtained pointer pointing to the header of the image data memory
#  @retval Success: @ref SCI_CAMERA_OK "SCI_CAMERA_OK"
#  @retval Other references: @ref SciCamErrorDefine.h "Error Code List"
#  @remarks The image data memory here is allocated by the SDK and will be destroyed with the payload.
def SciCam_Payload_GetImage(payload, pImg):
	SciCamCtrlDll.SciCam_Payload_GetImage.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))
	SciCamCtrlDll.SciCam_Payload_GetImage.restype = ctypes.c_uint
	return SciCamCtrlDll.SciCam_Payload_GetImage(payload, pImg)

## @ingroup module_PayloadParsingInterface_Generic
#  @~chinese
#  @brief ����payload���ݽ����õ��Զ���chunk data�б�
#  @param payload		[IN]  ָ��payload����ͷָ��
#  @param pChunkList	[OUT] ��ȡ����chunk data�б�����ϸ�ο��� @ref PSCI_CAM_CHUNK_LIST "PSCI_CAM_CHUNK_LIST"
#  @retval �ɹ��� @ref SCI_CAMERA_OK "SCI_CAMERA_OK"(0)
#  @retval �����μ�: @ref SciCamErrorDefine.h "״̬��"
#  @remarks NULL
#  @~english
#  @brief Obtain a custom chunk data list by parsing payload data
#  @param payload		[IN]  Pointer to the head of payload data
#  @param pAttr			[OUT] List of obtained chunk data, references: @ref PSCI_CAM_CHUNK_LIST "PSCI_CAM_CHUNK_LIST"
#  @retval Success: @ref SCI_CAMERA_OK "SCI_CAMERA_OK"
#  @retval Other references: @ref SciCamErrorDefine.h "Error Code List"
#  @remarks NULL
def SciCam_Payload_GetChunkList(payload, pChunkList):
	SciCamCtrlDll.SciCam_Payload_GetChunkList.argtypes = (ctypes.c_void_p, PSCI_CAM_CHUNK_LIST)
	SciCamCtrlDll.SciCam_Payload_GetChunkList.restype = ctypes.c_uint
	return SciCamCtrlDll.SciCam_Payload_GetChunkList(payload, ctypes.byref(pChunkList))

## @ingroup module_PayloadParsingInterface_Convert
#  @~chinese
#  @brief ͼ�����ظ�ʽת��
#  @param imgAttr		[IN]      Դͼ��������Ϣ����ϸ�ο��� @ref PSCI_CAM_IMAGE_ATTRIBUTE "PSCI_CAM_IMAGE_ATTRIBUTE"
#  @param srcImg		[IN]      ָ��Դͼ�������ڴ�ͷָ��
#  @param outType		[IN]      Ŀ��ͼ���������ͣ���ϸ�ο��� @ref SciCamPixelType "SciCamPixelType"
#  @param dstImg		[IN][OUT] ָ��Ŀ��ͼ�������ڴ�ͷָ��
#  @param dstImgSize	[IN][OUT] Ŀ��ͼ�����ݴ�С
#  @param zoom			[IN]      �Ƿ���������
#  @retval �ɹ��� @ref SCI_CAMERA_OK "SCI_CAMERA_OK"(0)
#  @retval �����μ�: @ref SciCamErrorDefine.h "״̬��"
#  @remarks Ŀǰ֧�ֵ�ɫͼ��ʽ��Mono8s/Mono8/Mono16�Ͳ�ɫͼ��ʽ:RGB8/RGB16�� \n
#  			outType��������ΪPixelTypeUnknown����ʱĬ�ϸ���Դ��ʽ����ת���� \n
#  			zoom����Ϊ��ͼ�����λ������ͬ��תʱ��Ч��zoomΪfalseʱ��ʾ�����������Ŵ�����Ϊtrueʱ���������Ŵ���������������ͼ������ֵ�Ǿ����Ŵ󣬲���ԭʼ���ݣ� \n
#  			��dstImgΪ��ʱ���ɻ�ȡĿ��ͼ�����ݴ�С���ɸ��ݵõ���dstImgSizeԤ�ȷ���dstImg�ڴ棬Ȼ���ٴ���dstImgָ����л�ȡĿ��ͼ�����ݡ�
#  		ע�⣬�˴�������RGB����BGR�Ĳ�ɫͼ��תΪRGB���У����ܴ�����B��Rͨ���෴������ʹ�� @ref SciCam_Payload_ConvertImage "SciCam_Payload_ConvertImage"�ӿڿɽ�������⣻
#  @~english
#  @brief Image Pixel Format Conversion
#  @param imgAttr		[IN]      Source Image Property Information, references: @ref PSCI_CAM_IMAGE_ATTRIBUTE "PSCI_CAM_IMAGE_ATTRIBUTE"
#  @param srcImg		[IN]      Pointer to the head of source image data memory
#  @param outType		[IN]      Target Image Pixel Type, references: @ref SciCamPixelType "SciCamPixelType"
#  @param dstImg		[IN][OUT] Pointer to the head of target image data memory
#  @param dstImgSize	[IN][OUT] Size of target image data
#  @param zoom			[IN]      Pixel scaling
#  @retval Success: @ref SCI_CAMERA_OK "SCI_CAMERA_OK"
#  @retval Other references: @ref SciCamErrorDefine.h "Error Code List"
#  @remarks Currently supported monochrome image formats: Mono8s/Mono8/Mono16, and color image formats: RGB8/RGB16. \n
#  			outType can be set to PixelTypeUnknown, in which case it will be converted based on the source format by default. \n
#  			The "zoom" parameter is effective when converting images with different pixel depths. When "zoom" is set to false, it means no pixel scaling is performed. When set to true, pixel scaling is applied, but the brightness values in the saved image are magnified and not the original data. \n
#  			When dstImg is empty, you can obtain the size of the target image data. Based on the obtained dstImgSize, pre-allocate memory for dstImg, and then pass the dstImg pointer to retrieve the target image data.
#  		Note that both RGB and BGR color images are converted to RGB arrangement here, and there may be a phenomenon that the B and R channels are reversed. To solve this problem, you can use the @ref SciCam_Payload_ConvertImage "SciCam_Payload_ConvertImage" interface;
def SciCam_Payload_ConvertImage(imgAttr, srcImg, outType, dstImg, dstImgSize, zoom):
	SciCamCtrlDll.SciCam_Payload_ConvertImage.argtypes = (PSCI_CAM_IMAGE_ATTRIBUTE, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool)
	SciCamCtrlDll.SciCam_Payload_ConvertImage.restype = ctypes.c_uint
	if dstImg == None:
		return SciCamCtrlDll.SciCam_Payload_ConvertImage(imgAttr, srcImg, ctypes.c_int(outType), dstImg, ctypes.byref(dstImgSize), ctypes.c_bool(zoom))
	return SciCamCtrlDll.SciCam_Payload_ConvertImage(imgAttr, srcImg, ctypes.c_int(outType), ctypes.byref(dstImg), ctypes.byref(dstImgSize), ctypes.c_bool(zoom))

## @ingroup module_PayloadParsingInterface_Convert
#  @~chinese
#  @brief ͼ�����ظ�ʽת����չ�ӿ�
#  @param imgAttr		[IN]      Դͼ��������Ϣ����ϸ�ο��� @ref PSCI_CAM_IMAGE_ATTRIBUTE "PSCI_CAM_IMAGE_ATTRIBUTE"
#  @param srcImg		[IN]      ָ��Դͼ�������ڴ�ͷָ��
#  @param outType		[IN]      Ŀ��ͼ���������ͣ���ϸ�ο��� @ref SciCamPixelType "SciCamPixelType"
#  @param dstImg		[IN][OUT] ָ��Ŀ��ͼ�������ڴ�ͷָ��
#  @param dstImgSize	[IN][OUT] Ŀ��ͼ�����ݴ�С
#  @param zoom			[IN]      �Ƿ���������
#  @param algorithmType	[IN]      �㷨���Ͳ�������bayer����תrgb����ʱ��ֵ��ʽ��0��ʾ���٣�1��ʾ���⣬2��ʾ����
#  @retval �ɹ��� @ref SCI_CAMERA_OK "SCI_CAMERA_OK"(0)
#  @retval �����μ�: @ref SciCamErrorDefine.h "״̬��"
#  @remarks outType��������ΪPixelTypeUnknown����ʱĬ�ϸ���Դ��ʽ����ת���� \n
#  			zoom����Ϊ��ͼ�����λ������ͬ��תʱ��Ч��zoomΪfalseʱ��ʾ�����������Ŵ�����Ϊtrueʱ���������Ŵ���������������ͼ������ֵ�Ǿ����Ŵ󣬲���ԭʼ���ݣ� \n
#  			��dstImgΪ��ʱ���ɻ�ȡĿ��ͼ�����ݴ�С���ɸ��ݵõ���dstImgSizeԤ�ȷ���dstImg�ڴ棬Ȼ���ٴ���dstImgָ����л�ȡĿ��ͼ�����ݡ�
#  		algorithmTypeĬ��Ϊ0�������������ͼ��ת������ѡ��2(����)������ע��˴���0(����)����ʱ��̣���2(����)����ʱ���
#  @~english
#  @brief Image pixel format conversion extension interface
#  @param imgAttr		[IN]      Source Image Property Information, references: @ref PSCI_CAM_IMAGE_ATTRIBUTE "PSCI_CAM_IMAGE_ATTRIBUTE"
#  @param srcImg		[IN]      Pointer to the head of source image data memory
#  @param outType		[IN]      Target Image Pixel Type, references: @ref SciCamPixelType "SciCamPixelType"
#  @param dstImg		[IN][OUT] Pointer to the head of target image data memory
#  @param dstImgSize	[IN][OUT] Size of target image data
#  @param zoom			[IN]      Pixel scaling
#  @param algorithmType	[IN]      Algorithm type parameter; when converting from bayer type to rgb type: 0 means bilinear algorithm, 1 means edge detection algorithm
#  @retval Success: @ref SCI_CAMERA_OK "SCI_CAMERA_OK"
#  @retval Other references: @ref SciCamErrorDefine.h "Error Code List"
#  @remarks outType can be set to PixelTypeUnknown, in which case it will be converted based on the source format by default. \n
#  			The "zoom" parameter is effective when converting images with different pixel depths. When "zoom" is set to false, it means no pixel scaling is performed. When set to true, pixel scaling is applied, but the brightness values in the saved image are magnified and not the original data. \n
#  			When dstImg is empty, you can obtain the size of the target image data. Based on the obtained dstImgSize, pre-allocate memory for dstImg, and then pass the dstImg pointer to retrieve the target image data.
#  		The default value of algorithmType is 0. For high-quality image conversion, you can choose "2(Best)" from the drop-down list. Please note that "0(Fast)" has the shortest processing time while "2(Best)" has the longest processing time.
def SciCam_Payload_ConvertImageEx(imgAttr, srcImg, outType, dstImg, dstImgSize, zoom, algorithmType):
	SciCamCtrlDll.SciCam_Payload_ConvertImageEx.argtypes = (PSCI_CAM_IMAGE_ATTRIBUTE, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool, ctypes.c_int)
	SciCamCtrlDll.SciCam_Payload_ConvertImageEx.restype = ctypes.c_uint
	if dstImg == None:
		return SciCamCtrlDll.SciCam_Payload_ConvertImageEx(imgAttr, srcImg, ctypes.c_int(outType), dstImg, ctypes.byref(dstImgSize), ctypes.c_bool(zoom), ctypes.c_int(algorithmType))
	return SciCamCtrlDll.SciCam_Payload_ConvertImageEx(imgAttr, srcImg, ctypes.c_int(outType), ctypes.byref(dstImg), ctypes.byref(dstImgSize), ctypes.c_bool(zoom), ctypes.c_int(algorithmType))

## @ingroup module_PayloadParsingInterface_Convert
#  @~chinese
#  @brief ����ͼ�񵽱���Ӳ��
#  @param filePath		[IN]  �ļ�·�����磺"D:\img.png"
#  @param pixelType		[IN]  ͼ���������ͣ���ϸ�ο��� @ref SciCamPixelType "SciCamPixelType"
#  @param img			[IN]  ָ��ͼ�������ڴ�ͷָ��
#  @param width			[IN]  ͼ��Ŀ���
#  @param height		[IN]  ͼ��ĸ߶�
#  @retval �ɹ��� @ref SCI_CAMERA_OK "SCI_CAMERA_OK"(0)
#  @retval �����μ�: @ref SciCamErrorDefine.h "״̬��"
#  @remarks zoom����Ϊ��ͼ�����λ������ͬ��תʱ��Ч��zoomΪfalseʱ��ʾ�����������Ŵ�����Ϊtrueʱ���������Ŵ���������������ͼ������ֵ�Ǿ����Ŵ󣬲���ԭʼ���ݣ�
#  @~english
#  @brief Save the image to the local hard disk.
#  @param filePath		[IN]  File path, for example: "D:\img.png"
#  @param pixelType		[IN]  Image pixel type, references: @ref SciCamPixelType "SciCamPixelType"
#  @param img			[IN]  Pointer to the header of the image data memory
#  @param width			[IN]  Image width
#  @param height		[IN]  Image height
#  @retval Success: @ref SCI_CAMERA_OK "SCI_CAMERA_OK"
#  @retval Other references: @ref SciCamErrorDefine.h "Error Code List"
#  @remarks The "zoom" parameter is effective when converting images with different pixel depths. When "zoom" is set to false, it means no pixel scaling is performed. When set to true, pixel scaling is applied, but the brightness values in the saved image are magnified and not the original data.
def SciCam_Payload_SaveImage(filePath, pixelType, img, width, height):
	# C prototype: SCI_CAM_API unsigned int SCICALL SciCam_Payload_SaveImage(IN const char* filePath, IN SciCamPixelType pixelType, IN void* img, IN uint64_t width, IN uint64_t height);
	SciCamCtrlDll.SciCam_Payload_SaveImage.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_int64, ctypes.c_int64)
	SciCamCtrlDll.SciCam_Payload_SaveImage.restype = ctypes.c_uint
	return SciCamCtrlDll.SciCam_Payload_SaveImage(filePath.encode('ascii'), ctypes.c_int(pixelType), img, ctypes.c_int64(width), ctypes.c_int64(height))

## @ingroup module_PayloadParsingInterface_LP3D
#  @~chinese
#  @brief ��payload�����л�ȡԪ���ݣ�LP3D��
#  @param payload		[IN]  ָ��payload����ͷָ��
#  @param pMeta			[OUT] ��ȡ����Ԫ���ݣ���ϸ�ο��� @ref PSCI_CAM_LP3D_META "PSCI_CAM_LP3D_META"
#  @retval �ɹ��� @ref SCI_CAMERA_OK "SCI_CAMERA_OK"(0)
#  @retval �����μ�: @ref SciCamErrorDefine.h "״̬��"
#  @remarks NULL
#  @~english
#  @brief Extract metadata from payload Data(LP3D)
#  @param payload		[IN]  Pointer to the head of payload data
#  @param pMeta			[OUT] Obtained Metadata, references: @ref PSCI_CAM_LP3D_META "PSCI_CAM_LP3D_META"
#  @retval Success: @ref SCI_CAMERA_OK "SCI_CAMERA_OK"
#  @retval Other references: @ref SciCamErrorDefine.h "Error Code List"
#  @remarks NULL
def SciCam_Payload_LP3D_GetMeta(payload, pMeta):
	SciCamCtrlDll.SciCam_Payload_LP3D_GetMeta.argtypes = (ctypes.c_void_p, PSCI_CAM_LP3D_META)
	SciCamCtrlDll.SciCam_Payload_LP3D_GetMeta.restype = ctypes.c_uint
	return SciCamCtrlDll.SciCam_Payload_LP3D_GetMeta(payload, ctypes.byref(pMeta))

## @ingroup module_PayloadParsingInterface_LP3D
#  @~chinese
#  @brief ��payload�����л�ȡͼ�����ݣ�LP3D��
#  @param payload		[IN]  ָ��payload����ͷָ��
#  @param pImage		[OUT] ��ȡ��ָ��ͼ�������ڴ�ͷָ��
#  @retval �ɹ��� @ref SCI_CAMERA_OK "SCI_CAMERA_OK"(0)
#  @retval �����μ�: @ref SciCamErrorDefine.h "״̬��"
#  @remarks pImage���ڴ���SDK���䣬��payload�������ڽ������ͷ�
#  @~english
#  @brief Extract image data from payload(LP3D)
#  @param payload		[IN]  Pointer to the head of payload data
#  @param pImage		[OUT] Obtain pointer to the head of image data memory
#  @retval Success: @ref SCI_CAMERA_OK "SCI_CAMERA_OK"
#  @retval Other references: @ref SciCamErrorDefine.h "Error Code List"
#  @remarks The memory for pImage is allocated by the SDK and is released upon the end of the payload's lifecycle.
def SciCam_Payload_LP3D_GetImage(payload, pImage):
	SciCamCtrlDll.SciCam_Payload_LP3D_GetImage.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))
	SciCamCtrlDll.SciCam_Payload_LP3D_GetImage.restype = ctypes.c_uint
	return SciCamCtrlDll.SciCam_Payload_LP3D_GetImage(payload, pImage)

## @ingroup module_PayloadParsingInterface_LP3D
#  @~chinese
#  @brief ��payload�����л�ȡ����������LP3D��
#  @param payload		[IN]  ָ��payload����ͷָ��
#  @param pointCounts	[OUT] ��ȡ������������
#  @retval �ɹ��� @ref SCI_CAMERA_OK "SCI_CAMERA_OK"(0)
#  @retval �����μ�: @ref SciCamErrorDefine.h "״̬��"
#  @remarks NULL
#  @~english
#  @brief Extract contour point count from payload data(LP3D)
#  @param payload		[IN]  Pointer to the head of payload data
#  @param pointCounts	[OUT] Number of obtained contour points
#  @retval Success: @ref SCI_CAMERA_OK "SCI_CAMERA_OK"
#  @retval Other references: @ref SciCamErrorDefine.h "Error Code List"
#  @remarks NULL
def SciCam_Payload_LP3D_GetPointCounts(payload, pointCounts):
	SciCamCtrlDll.SciCam_Payload_LP3D_GetPointCounts.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
	SciCamCtrlDll.SciCam_Payload_LP3D_GetPointCounts.restype = ctypes.c_uint
	return SciCamCtrlDll.SciCam_Payload_LP3D_GetPointCounts(payload, ctypes.byref(pointCounts))

## @ingroup module_PayloadParsingInterface_LP3D
#  @~chinese
#  @brief ��payload�����л�ȡ������LP3D��
#  @param payload		[IN]  ָ��payload����ͷָ��
#  @param dataType		[IN]  ָ�������������ͣ���ϸ�ο��� @ref SciCamPayloadDataType "SciCamPayloadDataType"
#  @param pContour		[OUT] ָ�����������ڴ�ͷָ��
#  @param invalidValue	[IN]  �趨��Ч���ֵ
#  @retval �ɹ��� @ref SCI_CAMERA_OK "SCI_CAMERA_OK"(0)
#  @retval �����μ�: @ref SciCamErrorDefine.h "״̬��"
#  @remarks NULL
#  @~english
#  @brief Retrieve contours from payload data(LP3D)
#  @param payload		[IN]  Pointer to the head of payload data
#  @param dataType		[IN]  Specify the contour data type. For details, please references: @ref SciCamPayloadDataType "SciCamPayloadDataType"
#  @param pContour		[OUT] Pointer to the head of contour data memory
#  @param invalidValue	[IN]  Set the value for invalid points
#  @retval Success: @ref SCI_CAMERA_OK "SCI_CAMERA_OK"
#  @retval Other references: @ref SciCamErrorDefine.h "Error Code List"
#  @remarks NULL
def SciCam_Payload_LP3D_GetContour(payload, dataType, pContour, invalidValue):
	SciCamCtrlDll.SciCam_Payload_LP3D_GetContour.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
	SciCamCtrlDll.SciCam_Payload_LP3D_GetContour.restype = ctypes.c_uint
	return SciCamCtrlDll.SciCam_Payload_LP3D_GetContour(payload, ctypes.c_int(dataType), ctypes.byref(pContour), ctypes.byref(invalidValue))

## @ingroup module_PayloadParsingInterface_LP3D
#  @~chinese
#  @brief ��payload�����лҶ�ֵ���ݣ�LP3D��
#  @param payload		[IN]  ָ��payload����ͷָ��
#  @param pGray			[OUT] ��ȡ��ָ��Ҷ�ֵ�����ڴ�ͷָ��
#  @retval �ɹ��� @ref SCI_CAMERA_OK "SCI_CAMERA_OK"(0)
#  @retval �����μ�: @ref SciCamErrorDefine.h "״̬��"
#  @remarks NULL
#  @~english
#  @brief Extract grayscale value data from payload(LP3D)
#  @param payload		[IN]  Pointer to the head of payload data
#  @param pGray			[OUT] Obtain pointer to the head of grayscale value data memory
#  @retval Success: @ref SCI_CAMERA_OK "SCI_CAMERA_OK"
#  @retval Other references: @ref SciCamErrorDefine.h "Error Code List"
#  @remarks NULL
def SciCam_Payload_LP3D_GetGray(payload, pGray):
	SciCamCtrlDll.SciCam_Payload_LP3D_GetGray.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
	SciCamCtrlDll.SciCam_Payload_LP3D_GetGray.restype = ctypes.c_uint
	return SciCamCtrlDll.SciCam_Payload_LP3D_GetGray(payload, ctypes.byref(pGray))

## @ingroup module_PayloadParsingInterface_SL3D
#  @~chinese
#  @brief ��payload�����л�ȡԪ���ݣ�SL3D��
#  @param payload		[IN]  ָ��payload����ͷָ��
#  @param pMeta			[OUT] ��ȡ����Ԫ���ݣ���ϸ�ο��� @ref PSCI_CAM_SL3D_META "PSCI_CAM_SL3D_META"
#  @retval �ɹ��� @ref SCI_CAMERA_OK "SCI_CAMERA_OK"(0)
#  @retval �����μ�: @ref SciCamErrorDefine.h "״̬��"
#  @remarks NULL
#  @~english
#  @brief Extract metadata from payload Data(SL3D)
#  @param payload		[IN]  Pointer to the head of payload data
#  @param pMeta			[OUT] Obtained Metadata, references: @ref PSCI_CAM_SL3D_META "PSCI_CAM_SL3D_META"
#  @retval Success: @ref SCI_CAMERA_OK "SCI_CAMERA_OK"
#  @retval Other references: @ref SciCamErrorDefine.h "Error Code List"
#  @remarks NULL
def SciCam_Payload_SL3D_GetMeta(payload, pMeta):
	SciCamCtrlDll.SciCam_Payload_SL3D_GetMeta.argtypes = (ctypes.c_void_p, PSCI_CAM_SL3D_META)
	SciCamCtrlDll.SciCam_Payload_SL3D_GetMeta.restype = ctypes.c_uint
	return SciCamCtrlDll.SciCam_Payload_SL3D_GetMeta(payload, pMeta)

## @ingroup module_PayloadParsingInterface_SL3D
#  @~chinese
#  @brief ��payload�л�ȡĿ�����ݣ�SL3D��
#  @param payload		[IN]  ָ��payload����ͷָ��
#  @param tgDataType	[IN]  Ŀ���������ͣ���ϸ�ο��� @ref SciCamPayloadSL3DTargetDataType "SciCamPayloadSL3DTargetDataType"
#  @param pData			[OUT] Ŀ������ 
#  @retval �ɹ��� @ref SCI_CAMERA_OK "SCI_CAMERA_OK"(0)
#  @retval �����μ�: @ref SciCamErrorDefine.h "״̬��"
#  @remarks @ref PSCI_CAM_SL3D_DATA "PSCI_CAM_SL3D_DATA" pData�е�dataΪǳ��������payload�������ڽ����Զ��ͷš�
#  @~english
#  @brief Extract metadata from payload Data(SL3D)
#  @param payload		[IN]  Pointer to the head of payload data
#  @param pMeta			[OUT] Target data type, references: @ref SciCamPayloadSL3DTargetDataType "SciCamPayloadSL3DTargetDataType"
#  @param pData			[OUT] Target data 
#  @retval Success: @ref SCI_CAMERA_OK "SCI_CAMERA_OK"
#  @retval Other references: @ref SciCamErrorDefine.h "Error Code List"
#  @remarks "data" in "pData" is shallow copied and automatically released when the payload's lifecycle ends.
def SciCam_Payload_SL3D_GetData(payload, tgDataType, pData):
	SciCamCtrlDll.SciCam_Payload_SL3D_GetData.argtypes = (ctypes.c_void_p, ctypes.c_int, PSCI_CAM_SL3D_DATA)
	SciCamCtrlDll.SciCam_Payload_SL3D_GetData.restype = ctypes.c_uint
	return SciCamCtrlDll.SciCam_Payload_SL3D_GetData(payload, tgDataType, pData)