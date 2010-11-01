COMPILER = g++
INC = -I..
CCFLAGS = -g -Wall $(INC)
ARCHIVE = ar
DEPEND = makedepend
.SUFFIXES: .o .cpp

lib = lib_2.a
src = \
class_0.cpp \
class_1.cpp \
class_2.cpp \
class_3.cpp \
class_4.cpp \
class_5.cpp \
class_6.cpp \
class_7.cpp \
class_8.cpp \
class_9.cpp \
class_10.cpp \
class_11.cpp \
class_12.cpp \
class_13.cpp \
class_14.cpp \
class_15.cpp \
class_16.cpp \
class_17.cpp \
class_18.cpp \
class_19.cpp \
class_20.cpp \
class_21.cpp \
class_22.cpp \
class_23.cpp \
class_24.cpp \
class_25.cpp \
class_26.cpp \
class_27.cpp \
class_28.cpp \
class_29.cpp \
class_30.cpp \
class_31.cpp \
class_32.cpp \
class_33.cpp \
class_34.cpp \
class_35.cpp \
class_36.cpp \
class_37.cpp \
class_38.cpp \
class_39.cpp \
class_40.cpp \
class_41.cpp \
class_42.cpp \
class_43.cpp \
class_44.cpp \
class_45.cpp \
class_46.cpp \
class_47.cpp \
class_48.cpp \
class_49.cpp \
class_50.cpp \
class_51.cpp \
class_52.cpp \
class_53.cpp \
class_54.cpp \
class_55.cpp \
class_56.cpp \
class_57.cpp \
class_58.cpp \
class_59.cpp \
class_60.cpp \
class_61.cpp \
class_62.cpp \
class_63.cpp \
class_64.cpp \
class_65.cpp \
class_66.cpp \
class_67.cpp \
class_68.cpp \
class_69.cpp \
class_70.cpp \
class_71.cpp \
class_72.cpp \
class_73.cpp \
class_74.cpp \
class_75.cpp \
class_76.cpp \
class_77.cpp \
class_78.cpp \
class_79.cpp \
class_80.cpp \
class_81.cpp \
class_82.cpp \
class_83.cpp \
class_84.cpp \
class_85.cpp \
class_86.cpp \
class_87.cpp \
class_88.cpp \
class_89.cpp \
class_90.cpp \
class_91.cpp \
class_92.cpp \
class_93.cpp \
class_94.cpp \
class_95.cpp \
class_96.cpp \
class_97.cpp \
class_98.cpp \
class_99.cpp \


objects = $(patsubst %.cpp, %.o, $(src))

all: depend $(lib)

$(lib): $(objects)
	$(ARCHIVE) cr $@ $^
	touch $@

.cpp.o:
	$(COMPILER) $(CCFLAGS) -c $<

clean:
	@rm $(objects) $(lib) 2> /dev/null

depend:
	@$(DEPEND) $(INC) $(src)

