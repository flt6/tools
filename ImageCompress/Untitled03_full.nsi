; �ýű�ʹ�� HM VNISEdit �ű��༭���򵼲���

; ��װ�����ʼ���峣��
!define PRODUCT_NAME "ImageCompress"
!define PRODUCT_VERSION "1.1"
!define PRODUCT_PUBLISHER "52pojie.cn @ flt"
!define PRODUCT_URL "https://www.flt6.top/article/compressImageTool"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\7z.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

SetCompressor lzma

; ------ MUI �ִ����涨�� (1.67 �汾���ϼ���) ------
!include "MUI.nsh"

; MUI Ԥ���峣��
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; ��ӭҳ��
!insertmacro MUI_PAGE_WELCOME
; ���ѡ��ҳ��
!insertmacro MUI_PAGE_COMPONENTS
; ��װĿ¼ѡ��ҳ��
!insertmacro MUI_PAGE_DIRECTORY
; ��װ����ҳ��
!insertmacro MUI_PAGE_INSTFILES
; ��װ���ҳ��
!insertmacro MUI_PAGE_FINISH

; ��װж�ع���ҳ��
!insertmacro MUI_UNPAGE_INSTFILES

; ��װ�����������������
!insertmacro MUI_LANGUAGE "SimpChinese"

; ��װԤ�ͷ��ļ�
!insertmacro MUI_RESERVEFILE_INSTALLOPTIONS
; ------ MUI �ִ����涨����� ------

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "Setup.exe"
InstallDir "$PROGRAMFILES\ImageCompress"
InstallDirRegKey HKLM "${PRODUCT_UNINST_KEY}" "UninstallString"
ShowInstDetails show
ShowUnInstDetails show
BrandingText " "

Section "���ļ�" SEC01
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
  File "E:\tem\0821\b.dist\*.*"
  WriteRegStr HKCR "Directory\Background\shell\ImageCompress" "" "ѹ����ǰ�ļ���ͼƬ"
  WriteRegStr HKCR "Directory\Background\shell\ImageCompress\command" ""  '"$INSTDIR\b.exe" "%V"'
  WriteRegStr HKCR "*\shell\ImageCompress" "" "ѹ����ǰͼƬ"
  WriteRegStr HKCR "*\shell\ImageCompress\command" "" '"$INSTDIR\b.exe" "%1"'
SectionEnd


Section "ffmpeg" SEC02
  File "E:\tem\0821\compress\ffmpeg-essentials.7z"
  File "E:\tem\0821\compress\7z.exe"
  File "E:\tem\0821\compress\7z.dll"
  ExecWait '"$INSTDIR\7z.exe" e -aoa ffmpeg-essentials.7z ffmpeg-2024-08-18-git-7e5410eadb-essentials_build/bin/ffmpeg.exe'
SectionEnd

Section "����ͼƬ��ʽ" SEC03
  WriteRegStr HKCR ".png\shell\ImageCompress" "" "ѹ����ǰͼƬ"
  WriteRegStr HKCR ".png\shell\ImageCompress\command" "" '"$INSTDIR\b.exe" "%1"'
  WriteRegStr HKCR ".jpg\shell\ImageCompress" "" "ѹ����ǰͼƬ"
  WriteRegStr HKCR ".jpg\shell\ImageCompress\command" "" '"$INSTDIR\b.exe" "%1"'
  WriteRegStr HKCR ".gif\shell\ImageCompress" "" "ѹ����ǰͼƬ"
  WriteRegStr HKCR ".gif\shell\ImageCompress\command" "" '"$INSTDIR\b.exe" "%1"'
  WriteRegStr HKCR ".webp\shell\ImageCompress" "" "ѹ����ǰͼƬ"
  WriteRegStr HKCR ".webp\shell\ImageCompress\command" "" '"$INSTDIR\b.exe" "%1"'
  WriteRegStr HKCR ".jpeg\shell\ImageCompress" "" "ѹ����ǰͼƬ"
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

#-- ���� NSIS �ű��༭�������� Function ���α�������� Section ����֮���д���Ա��ⰲװ�������δ��Ԥ֪�����⡣--#

; �����������
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC01} ""
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC02} "���path��û��ffmpeg���빴ѡ"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC03} "��ͼƬ�Ҽ��˵�����ӡ�ѹ����ǰͼƬ��������jpg, jpeg, gif, webp, png������ɾ����ж����װ"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

/******************************
 *  �����ǰ�װ�����ж�ز���  *
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

#-- ���� NSIS �ű��༭�������� Function ���α�������� Section ����֮���д���Ա��ⰲװ�������δ��Ԥ֪�����⡣--#

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "��ȷʵҪ��ȫ�Ƴ� $(^Name) ���������е������" IDYES +2
  Abort
FunctionEnd

Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) �ѳɹ��ش����ļ�����Ƴ���"
FunctionEnd
