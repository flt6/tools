; 该脚本使用 HM VNISEdit 脚本编辑器向导产生

; 安装程序初始定义常量
!define PRODUCT_NAME "ImageCompress"
!define PRODUCT_VERSION "1.1"
!define PRODUCT_PUBLISHER "52pojie.cn @ flt"
!define PRODUCT_URL "https://www.flt6.top/article/compressImageTool"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\7z.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

SetCompressor lzma

; ------ MUI 现代界面定义 (1.67 版本以上兼容) ------
!include "MUI.nsh"

; MUI 预定义常量
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; 欢迎页面
!insertmacro MUI_PAGE_WELCOME
; 组件选择页面
!insertmacro MUI_PAGE_COMPONENTS
; 安装目录选择页面
!insertmacro MUI_PAGE_DIRECTORY
; 安装过程页面
!insertmacro MUI_PAGE_INSTFILES
; 安装完成页面
!insertmacro MUI_PAGE_FINISH

; 安装卸载过程页面
!insertmacro MUI_UNPAGE_INSTFILES

; 安装界面包含的语言设置
!insertmacro MUI_LANGUAGE "SimpChinese"

; 安装预释放文件
!insertmacro MUI_RESERVEFILE_INSTALLOPTIONS
; ------ MUI 现代界面定义结束 ------

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "Setup.exe"
InstallDir "$PROGRAMFILES\ImageCompress"
InstallDirRegKey HKLM "${PRODUCT_UNINST_KEY}" "UninstallString"
ShowInstDetails show
ShowUnInstDetails show
BrandingText " "

Section "主文件" SEC01
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
  File "E:\tem\0821\b.dist\*.*"
  WriteRegStr HKCR "Directory\Background\shell\ImageCompress" "" "压缩当前文件夹图片"
  WriteRegStr HKCR "Directory\Background\shell\ImageCompress\command" ""  '"$INSTDIR\b.exe" "%V"'
  WriteRegStr HKCR "*\shell\ImageCompress" "" "压缩当前图片"
  WriteRegStr HKCR "*\shell\ImageCompress\command" "" '"$INSTDIR\b.exe" "%1"'
SectionEnd


Section "ffmpeg" SEC02
  File "E:\tem\0821\compress\ffmpeg-essentials.7z"
  File "E:\tem\0821\compress\7z.exe"
  File "E:\tem\0821\compress\7z.dll"
  ExecWait '"$INSTDIR\7z.exe" e -aoa ffmpeg-essentials.7z ffmpeg-2024-08-18-git-7e5410eadb-essentials_build/bin/ffmpeg.exe'
SectionEnd

Section "关联图片格式" SEC03
  WriteRegStr HKCR ".png\shell\ImageCompress" "" "压缩当前图片"
  WriteRegStr HKCR ".png\shell\ImageCompress\command" "" '"$INSTDIR\b.exe" "%1"'
  WriteRegStr HKCR ".jpg\shell\ImageCompress" "" "压缩当前图片"
  WriteRegStr HKCR ".jpg\shell\ImageCompress\command" "" '"$INSTDIR\b.exe" "%1"'
  WriteRegStr HKCR ".gif\shell\ImageCompress" "" "压缩当前图片"
  WriteRegStr HKCR ".gif\shell\ImageCompress\command" "" '"$INSTDIR\b.exe" "%1"'
  WriteRegStr HKCR ".webp\shell\ImageCompress" "" "压缩当前图片"
  WriteRegStr HKCR ".webp\shell\ImageCompress\command" "" '"$INSTDIR\b.exe" "%1"'
  WriteRegStr HKCR ".jpeg\shell\ImageCompress" "" "压缩当前图片"
  WriteRegStr HKCR ".jpeg\shell\ImageCompress\command" "" '"$INSTDIR\b.exe" "%1"'
SectionEnd

Section -AdditionalIcons
  CreateDirectory "$SMPROGRAMS\ImageCompress"
  CreateShortCut "$SMPROGRAMS\ImageCompress\Uninstall.lnk" "$INSTDIR\uninst.exe"
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\7z.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  Delete "$INSTDIR\7z.exe"
  Delete "$INSTDIR\7z.dll"
  Delete "$INSTDIR\ffmpeg-essentials.7z"
SectionEnd

#-- 根据 NSIS 脚本编辑规则，所有 Function 区段必须放置在 Section 区段之后编写，以避免安装程序出现未可预知的问题。--#

; 区段组件描述
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC01} ""
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC02} "如果path中没有ffmpeg，请勾选"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC03} "在图片右键菜单中添加“压缩当前图片”，关联jpg, jpeg, gif, webp, png，如需删除请卸载重装"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

/******************************
 *  以下是安装程序的卸载部分  *
 ******************************/

Section Uninstall
  Delete "$INSTDIR\uninst.exe"
  Delete "$INSTDIR\*.*"

  Delete "$SMPROGRAMS\ImageCompress\Uninstall.lnk"

  RMDir "$SMPROGRAMS\ImageCompress"

  RMDir "$INSTDIR"

  Delete "$APPDATA\compressImage\config.txt"
  RMDir "$APPDATA\compressImage"

  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
  DeleteRegKey HKCR "Directory\Background\shell\ImageCompress"
  DeleteRegKey HKCR "*\shell\ImageCompress"
  SetAutoClose false
SectionEnd

#-- 根据 NSIS 脚本编辑规则，所有 Function 区段必须放置在 Section 区段之后编写，以避免安装程序出现未可预知的问题。--#

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "您确实要完全移除 $(^Name) ，及其所有的组件？" IDYES +2
  Abort
FunctionEnd

Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) 已成功地从您的计算机移除。"
FunctionEnd
