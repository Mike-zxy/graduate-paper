TARGET=Juliet1.3

# Bins
MAKE=make
CC=gcc
CPP=g++
CFLAGS=-g
# 建议将包含路径单独列出
INCLUDES=-I testcasesupport/
# 链接库标志
LFLAGS=-lpthread

# Support files
SUPPORT_PATH=testcasesupport/
SUPPORT_SRCS=$(SUPPORT_PATH)main_linux.cpp $(SUPPORT_PATH)io.c $(SUPPORT_PATH)std_thread.c
# 这里手动指定 .o 转换，避免复杂的 prefix/suffix 嵌套导致路径错误
SUPPORT_OBJS=$(SUPPORT_PATH)main_linux.o $(SUPPORT_PATH)io.o $(SUPPORT_PATH)std_thread.o

# Partial files
MAKE_FILES=$(wildcard testcases/*/s*/Makefile) $(wildcard testcases/*/Makefile)
PARTIALS=$(patsubst %Makefile,%partial,$(MAKE_FILES))
INDIVIDUALS=$(patsubst %Makefile,%individuals,$(MAKE_FILES))

# 最终链接阶段
# 修改 $(TARGET) 部分
$(TARGET): $(PARTIALS) $(SUPPORT_OBJS)
	@echo "Creating object list..."
	# 将所有 .o 文件路径写入一个临时文件 object_list.txt
	@echo $(addsuffix .o,$(PARTIALS)) $(SUPPORT_OBJS) > object_list.txt
	# 使用 @ 符号告诉 g++ 从文件中读取参数
	$(CPP) $(CFLAGS) -I $(INCLUDES) -o $@ @object_list.txt $(LFLAGS)
	@rm object_list.txt
$(PARTIALS): 
	$(MAKE) -C $(dir $@) $(notdir $@).o

individuals: $(INDIVIDUALS)

$(INDIVIDUALS):
	$(MAKE) -C $(dir $@) $(notdir $@)

# 修复后的 Support Objects 编译规则
# 分别处理 .cpp 和 .c 文件
$(SUPPORT_PATH)main_linux.o: $(SUPPORT_PATH)main_linux.cpp
	$(CPP) $(CFLAGS) $(INCLUDES) -c $< -o $@

$(SUPPORT_PATH)io.o: $(SUPPORT_PATH)io.c
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

$(SUPPORT_PATH)std_thread.o: $(SUPPORT_PATH)std_thread.c
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

clean:
	rm -f $(TARGET) $(SUPPORT_OBJS)
	find testcases/ -name "*.o" -type f -delete
