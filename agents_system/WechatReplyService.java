package com.byefan.tactic.platform.agent.res.dev.service.impl;

import cn.hutool.core.collection.CollectionUtil;
import cn.hutool.core.date.DatePattern;
import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import com.byefan.tactic.platform.agent.common.constant.AgentConstant;
import com.byefan.tactic.platform.agent.common.model.entity.WechatPrompt;
import com.byefan.tactic.platform.agent.common.service.IWechatPromptService;
import com.byefan.tactic.platform.agent.project.model.entity.AgentProjectSessionUserSelected;
import com.byefan.tactic.platform.agent.project.service.IAgentProjectSessionUserSelectedService;
import com.byefan.tactic.platform.agent.res.dev.model.dto.*;
import com.byefan.tactic.platform.agent.res.dev.model.entity.WechatRecord;
import com.byefan.tactic.platform.agent.res.dev.model.entity.WechatRobot;
import com.byefan.tactic.platform.agent.res.dev.model.entity.WechatRobotTask;
import com.byefan.tactic.platform.agent.res.dev.model.entity.XhsUserResource;
import com.byefan.tactic.platform.agent.res.dev.service.*;
import com.byefan.tactic.platform.mapper.xhsUser.XhsUserInfoMapper;
import com.byefan.tactic.platform.model.entity.xhsUser.XhsUserInfo;
import com.byefan.tactic.platform.utils.Assert;
import com.byefan.tactic.platform.utils.LinkAndUuidConverterUtil;
import com.byefan.tactic.platform.utils.UrlUtils;
import com.byefan.tactic.platform.volcengine.VolcengineService;
import com.byefan.tactic.platform.volcengine.VolcengineServiceConfig;
import com.volcengine.ark.runtime.model.completion.chat.ChatCompletionRequest;
import com.volcengine.ark.runtime.model.completion.chat.ChatMessage;
import com.volcengine.ark.runtime.model.completion.chat.ChatMessageRole;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.tuple.Pair;
import org.apache.commons.lang3.tuple.Triple;
import org.springframework.amqp.core.AmqpTemplate;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@Slf4j
@Service
public class WechatReplyService implements IWechatReplyService {
    @Resource
    private RedisTemplate redisTemplate;
    @Resource
    private IWechatParamService wechatParamService;
    @Resource
    private StringRedisTemplate stringRedisTemplate;
    @Resource
    private IWechatRecordService wechatRecordService;
    @Resource
    private IWechatPromptService wechatPromptService;
    @Resource
    private XhsUserInfoMapper xhsUserInfoMapper;
    @Resource
    private IXhsUserResourceService xhsUserResourceService;
    @Resource
    private IWechatNoResourceUserService wechatNoResourceUserService;
    @Resource
    private IWechatRobotTaskService wechatRobotTaskService;
    @Resource
    private IWechatRobotService wechatRobotService;
    @Resource
    private IWechatUserAddService wechatUserAddService;
    @Resource
    private AmqpTemplate amqpTemplate;
    @Resource
    private VolcengineService volcengineService;
    @Resource
    private IAgentProjectSessionUserSelectedService agentProjectSessionUserSelectedService;

    /**
     * 背景: 一个达人 目前只有一个微信群  导致 全部项目沟通 都在这里面 进行
     * 目前流程有:
     * 1. 第一次询价
     * 2. 第二次询价
     * 3. 后面有的话 请继续补充
     * @param wechatDto 微信用户发送的消息
     * @return
     */
    @Override
    public WechatRecord saveAndReply2(WechatDto wechatDto) {
        WechatRecord wechatRecord;

        AgentProjectSessionUserSelected userSelected = agentProjectSessionUserSelectedService.queryCoordinateUserInfo(wechatDto.getName());
        if (Objects.nonNull(userSelected)){
            wechatRecord = getWechatRecord_2(wechatDto,userSelected);
        }else {
            wechatRecord = getWechatRecord_1(wechatDto);
        }


        return Objects.nonNull(wechatRecord) ? wechatRecord : null;
    }


    /**
     * 第一次询价
     * @param wechatDto
     * @return
     */
    public WechatRecord getWechatRecord_1(WechatDto wechatDto) {
        // 是否重置会话
        boolean clear = Objects.nonNull(wechatDto) && Objects.equals("重置", wechatDto.getMessage());
        String name = wechatDto.getName();
        if (clear) {
            wechatRecordService.deleteByName(name);
        } else {
            if (matchEmoji(wechatDto.getMessage()) || laQun(wechatDto.getMessage())) {
                return null;
            }
        }

        XhsUserResource userResource = xhsUserResourceService.getUser(name);
        if (Objects.isNull(userResource)) {
            if (LinkAndUuidConverterUtil.isUserUuid(name)) {
                try {
                    wechatNoResourceUserService.save(name);
                } catch (Exception e) {
                }
            }
            // 1、未找到对应的人、也要保存微信用户的消息
            wechatRecordService.save(wechatDto);
            return null;
        } else {
            if (!XhsUserResource.WECHAT_ADD_STATUS_SUCCESS.equals(userResource.getWechatAddStatus())) {
                // 添加微信成功、则更新
                wechatUserAddService.wechatAddSuccess(new WechatFriendAddDto(name));
            }
            if (!clear && Objects.equals(userResource.getChatStatus(), 1)) {
                // 聊天结束、不回复消息，也不保存消息
                if (!wechatDto.isNewModelReply()) {
                    return null;
                }
            }
        }

        if (Objects.isNull(wechatDto.getZhongCanWechat())) {
            wechatDto.setZhongCanWechat(userResource.getZhongCanWechat());
        }

        // 1、保存微信用户的消息
        WechatRecord wechatRecord = wechatRecordService.save(wechatDto);
        if (Objects.isNull(wechatRecord)) {
            log.error("保存微信用户的消息失败：微信用户：{}", name);
            return null;
        }

        String output = null;
        if (clear || this.startsWithGreeting(wechatRecord.getMessage())) {
            if (clear) {
                xhsUserResourceService.updateChatStatus(userResource.getUserUuid(), 0);
            }
            WechatPrompt byPromptTypeAndStep = wechatPromptService.getByPromptTypeAndStep("建联微信智能体", "开场语");
            if (Objects.isNull(byPromptTypeAndStep)) {
                output = "宝子你好～辛苦确认一下这个主页链接是不是你呀～ " + LinkAndUuidConverterUtil.uuidToUserLink(userResource.getUserUuid()) + " 这边有个小红书广告要跟你合作";
            } else {
                output = byPromptTypeAndStep.getPromptWord()
                        .replace("{userName}", userResource.getNickname())
                        .replace("{userLink}", LinkAndUuidConverterUtil.uuidToUserLink(userResource.getUserUuid()));
            }
        } else {
            // 如果用户填的是主页链接，就把主页链接替换成昵称
            this.replaceUserLinkWithNickname(wechatRecord);
            if (wechatDto.isNewModelReply()) {
                output = this.newChat(userResource, wechatRecord);
            } else {
                output = this.oldChat(userResource, wechatRecord);
            }
        }

        if (Objects.nonNull(output)) {
            wechatRecord.setMessageReply(output);
            wechatRecordService.updateMessageReply(wechatRecord.getId(), output);
        }
        return wechatRecord;
    }

    /**
     * 第二次询价
     * @param wechatDto
     * @param userSelected
     * @return
     */
    private WechatRecord getWechatRecord_2(WechatDto wechatDto, AgentProjectSessionUserSelected userSelected) {
        String name = wechatDto.getName();
        // 1.保存微信用户的消息
        WechatRecord wechatRecord = wechatRecordService.save(wechatDto);
        if (Objects.isNull(wechatRecord)) {
            log.error("保存微信用户的消息失败：微信用户：{}", name);
            return null;
        }

        //2. 按AgentProjectSessionUserSelected.cooperationTime 开始合作时间 查询后续聊天内容
        List<WechatRecord> wechatRecords = wechatRecordService.listRecord(wechatDto.getName(), userSelected.getCooperationTime(), null);
        if (CollectionUtil.isEmpty(wechatRecords))
            return null;
        //3.二次议价 返回信息  并修改达人二次议价状态
        String output =  agentProjectSessionUserSelectedService.getSecondBargainingMessage(userSelected,wechatRecords,wechatDto);
        if (StringUtils.isNotEmpty(output)) {
            wechatRecord.setMessageReply(output);
            wechatRecordService.updateMessageReply(wechatRecord.getId(), output);
        }
        return wechatRecord;
    }

    private String oldChat(XhsUserResource userResource, WechatRecord wechatRecord) {
        // 2、获取系统提示词、以及最近聊天记录、组装 提示词
        List<ChatMessage> chatMessage = this.getChatMessage(userResource, wechatRecord);
        if (CollectionUtil.isEmpty(chatMessage)) {
            return null;
        }
        String output = null;
        Pair<String, String> chat = null;
        try {
            // chat = VolcengineService.chat(chatMessage);
            chat = VolcengineService.chat(chatMessage, VolcengineServiceConfig.MODEL_DOUBAO_1_5_pro_32k_CHAT, 0.7D, 0.1D);
            if (Objects.nonNull(chat) && Objects.nonNull(chat.getValue())) {
                output = chat.getValue();
            }

            if (Objects.isNull(output)) {
                log.error("微信聊天大模型回复返回空：{}" + chat);
                return null;
            }

            String outputJson = VolcengineService.extractJsonContent(output);
            if (Objects.nonNull(outputJson)) {
                JSONObject jsonObject = JSONUtil.parseObj(outputJson);
                String message = jsonObject.getStr("message");
                if (Objects.nonNull(message)) {
                    output = message;
                }
                // 会话是否结束标记
                String chatEnd = jsonObject.getStr("chatEnd");
                if (Boolean.TRUE.toString().equals(chatEnd)) {
                    xhsUserResourceService.updateChatStatus(userResource.getUserUuid(), 1);
                    try {
                        amqpTemplate.convertAndSend(AgentConstant.AGENT_USER_RESOURCE_CHAT_COMPLETE, new WechatChatCompleteDto(userResource.getUserUuid(), DatePattern.NORM_DATETIME_FORMATTER.format(wechatRecord.getMessageTime())));
                    } catch (Exception e) {
                        log.error("推送 对客沟通聊天完成 队列失败 {}", userResource.getUserUuid(), e);
                    }
                }
            }

            return output;
        } catch (Exception e) {
            log.error("微信聊天回复失败:{}", chat, e);
            return null;
        }
    }


    private String newChat(XhsUserResource xhsUserResource, WechatRecord wechatRecord) {
        // 1、
        WechatPrompt wechatPrompt = this.getWechatPrompt(WechatPrompt.PROMPT_TYPE_WECHAT_REPLY, "1统筹智能体-提示词（流程优先版）");

        String name = xhsUserResource.getNickname();
        String productName = xhsUserResource.getProjectName();
        Integer state = xhsUserResource.getChatStatus();

        List<WechatRecord> wechatRecordList = wechatRecordService.listRecord(wechatRecord.getName(), 100, 0);
        wechatRecordList = wechatRecordList.stream().filter(record -> !record.getId().equals(wechatRecord.getId())).collect(Collectors.toList());
        StringBuilder sb = new StringBuilder();
        for (WechatRecord record : wechatRecordList) {
            if (StrUtil.isNotEmpty(record.getMessage()) && !Objects.equals(record.getMessage(), "重置")) {
                sb.append("{\"role\":\"user\",\"content\":\"" + record.getMessage() + "\"}");
            }

            if (StrUtil.isNotEmpty(record.getMessageReply())) {
                sb.append("{\"role\":\"assistant\",\"content\":\"" + record.getMessageReply() + "\"}");
            }
        }
        String chatRecords = sb.toString();
        String promptWord = wechatPrompt.getPromptWord()
                .replaceAll("\\{\\{outputList\\}\\}", chatRecords)
                .replaceAll("\\{\\{input\\}\\}", wechatRecord.getMessage())
                .replaceAll("\\{\\{product\\}\\}", productName)
                .replaceAll("\\{\\{name\\}\\}", name)
                .replaceAll("\\{\\{state\\}\\}", state + "");

        Triple<String, String, String> triple = this.callVolcengineModel(wechatPrompt, this.getChatMessage(promptWord));
        if (Objects.isNull(triple) && Objects.isNull(triple.getRight())) {
            return null;
        }

        String result = triple.getRight();
        if (Objects.equals("000", result)) {
            wechatPrompt = this.getWechatPrompt(WechatPrompt.PROMPT_TYPE_WECHAT_REPLY, "2对话回复-提示词");

            // 对话
            int monthValue = LocalDate.now().plusMonths(1).getMonthValue();
            promptWord = wechatPrompt.getPromptWord()
                    .replaceAll("\\{\\{outputList\\}\\}", chatRecords)
                    .replaceAll("\\{\\{input\\}\\}", wechatRecord.getMessage())
                    .replaceAll("\\{\\{product\\}\\}", productName)
                    .replaceAll("\\{\\{name\\}\\}", name)
                    .replaceAll("x月图文报备价格", monthValue + "月图文报备价格")
                    .replaceAll("x月视频报备价格", monthValue + "月视频报备价格");
            triple = this.callVolcengineModel(wechatPrompt, this.getChatMessage(promptWord));
            if (Objects.isNull(triple) && Objects.isNull(triple.getRight())) {
                return null;
            }

            result = triple.getRight();
            String outputJson = VolcengineService.extractJsonContent(result);
            if (Objects.isNull(outputJson)) {
                return result;
            } else {
                return this.getOutput(outputJson, xhsUserResource, wechatRecord);
            }
        } else if (Objects.equals("001", result)) {
            wechatPrompt = wechatPromptService.getByPromptTypeAndStep(WechatPrompt.PROMPT_TYPE_WECHAT_REPLY, "3智能问答系统规范-提示词");

            // 问答
            promptWord = wechatPrompt.getPromptWord()
                    .replace("{{conversation}}", chatRecords)
                    .replace("{{input}}", wechatRecord.getMessage())
                    .replace("{{production}}", productName);

            triple = this.callVolcengineModel(wechatPrompt, this.getChatMessage(promptWord));
            if (Objects.isNull(triple)) {
                return null;
            }
            return triple.getRight();
        } else {
            log.error(WechatPrompt.PROMPT_TYPE_WECHAT_REPLY + "流程判定失败");
        }
        return null;
    }

    @Override
    public WechatMessageSendDto getSendMessage(String zhongCanWechat) {
        if (StrUtil.isEmpty(zhongCanWechat) || this.noAddTime()) {
            return null;
        }
        // 判断是否超过每天（24小时内）发消息的限制
        String everyDayMessageCount = "wechat:every_day_message_count:" + zhongCanWechat;
        redisTemplate.opsForValue().setIfAbsent(everyDayMessageCount, 0, Duration.ofHours(24));
        Object o = redisTemplate.opsForValue().get(everyDayMessageCount);
        if (Objects.nonNull(o) && (Long.valueOf(o.toString())) >= this.everyDayMaxCount()) {
            // 超过限制，不能发送消息
            return null;
        }

        String lockKey = "wechat:chat:getSendMessageLock:" + zhongCanWechat;
        Boolean aBoolean = stringRedisTemplate.opsForValue().setIfAbsent(lockKey, "1", 3, TimeUnit.SECONDS);
        if (!Objects.equals(aBoolean, true)) {
            return null;
        }
        try {
            WechatRobot wechatRobot = wechatRobotService.getByWechat(zhongCanWechat);
            if (Objects.isNull(wechatRobot)) {
                return null;
            }
            WechatRobotTask messageTask = wechatRobotTaskService.getTask(wechatRobot.getId(), 1);
            if (Objects.isNull(messageTask)) {
                return null;
            }
            WechatMessageSendDto wechatMessageSendDto = new WechatMessageSendDto();
            wechatMessageSendDto.setMessageTaskId(messageTask.getId());
            wechatMessageSendDto.setMessage(messageTask.getContent());
            wechatMessageSendDto.setName(messageTask.getUserUuid());
            wechatRecordService.saveSendMessage(messageTask.getUserUuid(), messageTask.getContent(), messageTask.getRobotId());
            wechatRobotTaskService.updateStatus(messageTask.getId(), 10, null);
            if (Objects.nonNull(messageTask.getAutoSendMessage()) && messageTask.getAutoSendMessage() == 1) {
                XhsUserResourceStatusDto statusDto = new XhsUserResourceStatusDto(messageTask.getUserUuid(), XhsUserResource.StageStatus.COMMUNICATE, XhsUserResource.ExecuteStatus.EXECUTING, null, 0);
                amqpTemplate.convertAndSend(AgentConstant.AGENT_USER_RESOURCE_UPDATE_STATUS, statusDto);
            }
            if (Objects.nonNull(wechatMessageSendDto)) {
                redisTemplate.opsForValue().increment(everyDayMessageCount);
            }
            return wechatMessageSendDto;
        } finally {
            stringRedisTemplate.delete(lockKey);
        }
    }

    @Override
    public boolean sendMessageMark(WechatMessageSendDto wechatMessageSendDto) {
        Assert.isNull(wechatMessageSendDto, "消息发送状态不能为空");
        Assert.isNull(wechatMessageSendDto.getMessageTaskId(), "消息任务ID不能为空");
        Assert.isNull(wechatMessageSendDto.getStatus(), "消息发送状态不能为空");
        Integer status = wechatMessageSendDto.getStatus();
        WechatRobotTask messageTask = wechatRobotTaskService.getById(wechatMessageSendDto.getMessageTaskId());
        if (Objects.nonNull(messageTask)) {
            String userUuid = messageTask.getUserUuid();
            boolean isUserUuid = LinkAndUuidConverterUtil.isUserUuid(userUuid);
            WechatRobot byId = wechatRobotService.getById(messageTask.getRobotId());
            if (!isUserUuid) {
                // 不是uuid就是 达人微信
                XhsUserResource xhsUserResource = xhsUserResourceService.getRobotWechatUserAndWechat(Objects.nonNull(byId) ? byId.getWechat() : null, userUuid);
                if (Objects.nonNull(xhsUserResource)) {
                    userUuid = xhsUserResource.getUserUuid();
                }
            }

            String statusStr = wechatMessageSendDto.getStatusStr();
            boolean b = wechatRobotTaskService.updateStatus(messageTask.getId(), status, statusStr);
            if (Objects.equals("邀请成功", statusStr)) {
                XhsUserResourceStatusDto statusDto = new XhsUserResourceStatusDto(userUuid, XhsUserResource.StageStatus.PULL_ENTERPRISE_WECHAT, XhsUserResource.ExecuteStatus.EXECUTED, statusStr, 0);
                amqpTemplate.convertAndSend(AgentConstant.AGENT_USER_RESOURCE_UPDATE_STATUS, statusDto);
            } else {
                wechatRecordService.saveSendMessage(userUuid, messageTask.getContent(), messageTask.getRobotId());
            }
            return b;
        } else {
            if (Objects.equals(status, 10)) {
                wechatRecordService.saveSendMessage(wechatMessageSendDto.getName(), wechatMessageSendDto.getMessage(), null);
            }
            return true;
        }
    }


    private boolean startsWithGreeting(String message) {
        if (message == null) {
            return false;
        }
        return message.startsWith("我通过了你的朋友验证请求，现在我们可以开始聊天了") ||
                message.startsWith("我通过了你的好友验证请求，现在我们可以开始聊天了") ||
                (message.contains("@") && message.contains("对接") && message.toUpperCase().contains("媒介PR"));
    }

    private void replaceUserLinkWithNickname(WechatRecord record) {
        String userLink = getUserLink(record);
        if (userLink != null) {
            String userUuid = LinkAndUuidConverterUtil.linkToUuid(userLink);
            String nickname = getUserNickname(userUuid);
            if (nickname != null) {
                String replaced = record.getMessage().replace(userLink, nickname);
                record.setMessage(replaced);
            }
        }
    }

    /**
     * 组装 提示词
     *
     * @param wechatRecord
     * @return
     */
    private List<ChatMessage> getChatMessage(XhsUserResource userResource, WechatRecord wechatRecord) {
        List<ChatMessage> messages = new ArrayList<>();
        String step = "自动聊天";
        WechatPrompt wechatPrompt = wechatPromptService.getByPromptTypeAndStep(WechatPrompt.PROMPT_TYPE_WECHAT_REPLY, step);
        Assert.isNull(wechatPrompt, "未找到系统提示词：" + WechatPrompt.PROMPT_TYPE_WECHAT_REPLY + "-" + step);

        String promptWord = wechatPrompt.getPromptWord();
        String userNickname = this.getUserNickname(userResource.getUserUuid());
        String name = Objects.nonNull(userNickname) ? userNickname : userResource.getNickname();
        promptWord = promptWord.replace("{{input}}", wechatRecord.getMessage())
                .replace("{{name}}", Objects.nonNull(name) ? name : "")
                .replace("{{product}}", Objects.nonNull(userResource.getProjectName()) ? userResource.getProjectName() : "")
                .replaceAll("\\{\\{month\\}\\}", LocalDate.now().plusMonths(1).getMonthValue() + "")
        ;

        messages.add(ChatMessage.builder().role(ChatMessageRole.SYSTEM).content(promptWord).build());

        // 历史对话
        List<WechatRecord> wechatRecordList = wechatRecordService.listRecord(wechatRecord.getName(), 20, 0);
        if (CollectionUtil.isNotEmpty(wechatRecordList)) {
            for (WechatRecord record : wechatRecordList) {
                if (Objects.equals(wechatRecord.getId(), record.getId())) {
                    continue;
                }
                if (Objects.nonNull(record.getMessage()) && !Objects.equals(record.getMessage(), "重置")) {
                    messages.add(ChatMessage.builder().role(ChatMessageRole.USER).content(record.getMessage()).build());
                }
                if (Objects.nonNull(record.getMessageReply())) {
                    messages.add(ChatMessage.builder().role(ChatMessageRole.ASSISTANT).content(record.getMessageReply()).build());
                }
            }
        }
        messages.add(ChatMessage.builder().role(ChatMessageRole.USER).content(wechatRecord.getMessage()).build());
        return messages;
    }

    /**
     * 获取 主页链接对应的小红书名称
     *
     * @param wechatRecord
     * @return
     */
    private String getUserLink(WechatRecord wechatRecord) {
        List<String> userLinks = UrlUtils.extractUserLinks(wechatRecord.getMessage());
        if (CollectionUtil.isNotEmpty(userLinks)) {
            return userLinks.get(0);
        }
        return null;
    }

    /**
     * 根据主页链接获取对应的小红书名称
     *
     * @param userUuid
     * @return
     */
    private String getUserNickname(String userUuid) {
        if (Objects.isNull(userUuid)) {
            return null;
        }
        XhsUserInfo byUuId = xhsUserInfoMapper.getByUuId(userUuid);
        if (Objects.nonNull(byUuId)) {
            return byUuId.getNickname();
        }
        return null;
    }

    /**
     * 匹配一个[XX] 或 多个 []的表情
     */
    private static final Pattern PATTERN_1 = Pattern.compile("\\[[^\\]]{0,10}\\](?:\\[[^\\]]{0,10}\\])*");
    /**
     * 匹配表情开头且后面最多10个字符
     */
    private static final Pattern PATTERN_2 = Pattern.compile("^表情.{0,10}");

    public static boolean matchEmoji(String value) {
        boolean matches1 = PATTERN_1.matcher(value).matches();
        if (matches1) {
//            System.out.println(value + ":匹配成功1");
            return true;
        }

        boolean matches2 = PATTERN_2.matcher(value).matches();
        if (matches2) {
//            System.out.println(value + ":匹配成功2");
            return true;
        }
        return false;
    }

    private static boolean laQun(String message) {
        if (Objects.isNull(message)) {
            return false;
        }
        return message.startsWith("拉博主") && message.endsWith("进群");
    }

    private int everyDayMaxCount() {
        return wechatParamService.getByTypeAndCode("wechat_robot_message", "everyday_message_send_limit", 10000);
    }

    private boolean noAddTime() {
        LocalTime now = LocalTime.now();
        return now.getHour() >= 0 && now.getHour() <= 8;
    }

    private WechatPrompt getWechatPrompt(String promptType, String step) {
        WechatPrompt wechatPrompt = wechatPromptService.getByPromptTypeAndStep(promptType, step);
        Assert.isNull(wechatPrompt, "未找到提示词：" + promptType + "-" + step);
        return wechatPrompt;
    }

    private List<ChatMessage> getChatMessage(String promptWord) {
        List<ChatMessage> messages = new ArrayList<>();
        messages.add(ChatMessage.builder().role(ChatMessageRole.SYSTEM).content(promptWord).build());
        return messages;
    }

    private Triple<String, String, String> callVolcengineModel(WechatPrompt wechatPrompt, List<ChatMessage> chatMessage) {
        ChatCompletionRequest.Builder builder = volcengineService.buildChatCompletionRequest(wechatPrompt.getModel(), wechatPrompt.getModelParam());
        builder.messages(chatMessage);
        Triple<String, String, String> chats = null;
        try {
            chats = volcengineService.chats(builder, false, 1);
        } catch (Exception e) {
            log.error("调用火山引擎模型失败");
        }
        return chats;
    }

    private String getOutput(String outputJson, XhsUserResource userResource, WechatRecord wechatRecord) {
        String output = null;
        if (Objects.nonNull(outputJson)) {
            JSONObject jsonObject = JSONUtil.parseObj(outputJson);
            String message = jsonObject.getStr("output");
            if (Objects.nonNull(message)) {
                output = message;
            }
            // 会话是否结束标记
            String chatEnd = jsonObject.getStr("state");
            if (Objects.equals(chatEnd, "1") || Objects.equals(chatEnd, "会话结束")) {
                xhsUserResourceService.updateChatStatus(userResource.getUserUuid(), 1);
                try {
                    amqpTemplate.convertAndSend(AgentConstant.AGENT_USER_RESOURCE_CHAT_COMPLETE, new WechatChatCompleteDto(userResource.getUserUuid(), DatePattern.NORM_DATETIME_FORMATTER.format(wechatRecord.getMessageTime())));
                } catch (Exception e) {
                    log.error("推送 对客沟通聊天完成 队列失败 {}", userResource.getUserUuid(), e);
                }
            } else {
                xhsUserResourceService.updateChatStatus(userResource.getUserUuid(), 0);
            }
        }
        return output;
    }
}
