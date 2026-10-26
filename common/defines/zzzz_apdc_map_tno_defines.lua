NDefines.NGame.MAP_SCALE_PIXEL_TO_KM = 7.827                    -- 7.82715176 --was 7.114

NDefines.NGraphics.GMT_OFFSET = 2560 -- X position on map, of Greenwitch GMT+0 (see also in shader daynight.fxh) #was 2793, now 2560 as Greenwich is located at 0°W/E.
NDefines.NGraphics.SOUTH_POLE_OFFSET = 0.17 -- Our map is missing big parts of globe on north and south (see also in shader daynight.fxh) #was 0.17
NDefines.NGraphics.NORTH_POLE_OFFSET = 0.93 -- #was 0.93

NDefines.NFrontend.CAMERA_LOOKAT_X = 2700.0 						-- originally 2958; Rotation point in main menu
NDefines.NFrontend.CAMERA_LOOKAT_Y = 0.0
NDefines.NFrontend.CAMERA_LOOKAT_Z = 2010.0						-- originally 1519
NDefines.NFrontend.CAMERA_START_X = 2700.0							-- originally 2958; Initial position in main menu
NDefines.NFrontend.CAMERA_START_Y = 825.0							-- Y is height
NDefines.NFrontend.CAMERA_START_Z = 2010.0							-- originally 1400
NDefines.NFrontend.CAMERA_END_X = 2700.0							-- originally 2958; Move to position in main menu
NDefines.NFrontend.CAMERA_END_Y = 825.0
NDefines.NFrontend.CAMERA_END_Z = 2010.0							-- originally 1400
NDefines.NFrontend.CAMERA_MIN_HEIGHT = 50.0						-- Minimum camera height
NDefines.NFrontend.CAMERA_MAX_HEIGHT = 3475.0						-- Maximum camera height # yes I know this number seems bizzare but it's the maximum height at which you cannot see a piece of land twice whilst also seeing the whole world
NDefines.NFrontend.CAMERA_SPEED_IN_MENUS = 0.1
NDefines.NFrontend.CAMERA_INTERPOLATION_SPEED = 0.19

NDefines.NFrontend.FRONTEND_POS_X = 2700.0 						-- originally 2958
NDefines.NFrontend.FRONTEND_POS_Y = 825.0
NDefines.NFrontend.FRONTEND_POS_Z = 2010.0							-- #tno 2085 #vanilla 1500
NDefines.NFrontend.FRONTEND_LOOK_X = 2700.0 						-- originally 2958
NDefines.NFrontend.FRONTEND_LOOK_Y = 0.0
NDefines.NFrontend.FRONTEND_LOOK_Z = 2010.0						-- originally 1519

NDefines.NFrontend.MP_OPTIONS_POS_X = 2700.0 						-- originally 2958
NDefines.NFrontend.MP_OPTIONS_POS_Y = 825.0
NDefines.NFrontend.MP_OPTIONS_POS_Z = 2010.0						-- originally 1500
NDefines.NFrontend.MP_OPTIONS_LOOK_X = 2700.0 						-- originally 2958
NDefines.NFrontend.MP_OPTIONS_LOOK_Y = 0.0
NDefines.NFrontend.MP_OPTIONS_LOOK_Z = 2010.0						-- originally 1519