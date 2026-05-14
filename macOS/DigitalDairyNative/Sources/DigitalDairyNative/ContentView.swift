import AppKit
import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        ZStack {
            VisualEffectBackground()
            LinearGradient(
                colors: [
                    Color(hex: model.themeStartHex).opacity(0.42),
                    Color(hex: model.themeEndHex).opacity(0.38),
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .allowsHitTesting(false)

            NavigationSplitView {
                List(selection: $model.sidebarSelection) {
                    Section("Digital Dairy") {
                        ForEach(AppModel.SidebarItem.allCases) { item in
                            Label(item.rawValue, systemImage: item == .run ? "play.circle" : "doc.richtext")
                                .tag(item)
                        }
                    }
                }
                .listStyle(.sidebar)
                .scrollContentBackground(.hidden)
                .background(.ultraThinMaterial)
                .navigationSplitViewColumnWidth(min: 200, ideal: 230, max: 280)
            } detail: {
                Group {
                    switch model.sidebarSelection {
                    case .run:
                        RunTabView()
                    case .settings:
                        ConfigEditorPanel()
                    }
                }
                .background(.regularMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                .padding(10)
            }
            .navigationTitle(AppModel.appName)
        }
        .alert(model.alertTitle, isPresented: $model.showAlert) {
            Button("好", role: .cancel) {}
        } message: {
            Text(model.alertMessage)
        }
    }
}

private struct RunTabView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        HSplitView {
            Form {
                Section("目录") {
                    LabeledContent("路径") {
                        Text(model.projectPathDisplay)
                            .font(.callout)
                            .textSelection(.enabled)
                            .multilineTextAlignment(.trailing)
                    }
                    if !model.isBundled {
                        Button("选择项目目录…") {
                            model.chooseProjectFolder()
                        }
                    } else {
                        Text("安装版已自动使用「文稿」目录")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                Section("快捷操作") {
                    Button("生成今日日报") { model.runDaily() }
                        .disabled(model.busy)
                    Button("仅采集（Dry Run）") { model.runDry() }
                        .disabled(model.busy)
                    Button("打开今日总结") { model.openTodaySummary() }
                    Button(model.isBundled ? "在 Finder 中打开数据目录" : "在 Finder 中打开项目") {
                        model.openInFinder()
                    }
                }

                Section("渐变主题") {
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .fill(
                            LinearGradient(
                                colors: [Color(hex: model.themeStartHex), Color(hex: model.themeEndHex)],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(height: 56)
                        .overlay {
                            RoundedRectangle(cornerRadius: 10, style: .continuous)
                                .strokeBorder(.white.opacity(0.35), lineWidth: 1)
                        }

                    ColorPicker("起始色", selection: hexBinding(\.themeStartHex))
                    ColorPicker("结束色", selection: hexBinding(\.themeEndHex))
                }
            }
            .formStyle(.grouped)
            .frame(minWidth: 280, idealWidth: 320, maxWidth: 400)
            .scrollContentBackground(.hidden)
            .background(.thinMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))

            RunLogPanel()
                .frame(minWidth: 360)
        }
        .padding(14)
    }

    private func hexBinding(_ keyPath: ReferenceWritableKeyPath<AppModel, String>) -> Binding<Color> {
        Binding(
            get: {
                Color(hex: model[keyPath: keyPath])
            },
            set: { newValue in
                if let cg = NSColor(newValue).usingColorSpace(.deviceRGB) {
                    let r = Int(round(cg.redComponent * 255))
                    let g = Int(round(cg.greenComponent * 255))
                    let b = Int(round(cg.blueComponent * 255))
                    model[keyPath: keyPath] = String(format: "#%02X%02X%02X", r, g, b)
                    model.saveTheme()
                }
            }
        )
    }
}

private struct RunLogPanel: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("运行日志")
                    .font(.title3.weight(.semibold))
                Spacer()
                Text(model.statusText)
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }

            ScrollView {
                Text(model.logText.isEmpty ? "（尚无输出）" : model.logText)
                    .font(.system(.body, design: .monospaced))
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .textSelection(.enabled)
            }
            .padding(10)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
        }
        .padding(10)
        .background(.thinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

private struct ConfigEditorPanel: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("配置文件")
                    .font(.title3.weight(.semibold))
                Spacer()
                Picker("", selection: $model.settingsDoc) {
                    ForEach(AppModel.SettingsDoc.allCases, id: \.self) { doc in
                        Text(doc.rawValue).tag(doc)
                    }
                }
                .pickerStyle(.segmented)
                .frame(maxWidth: 420)
            }

            if let err = model.settingsLoadError {
                Text(err)
                    .foregroundStyle(.secondary)
            }

            TextEditor(text: $model.settingsEditorText)
                .font(.system(.body, design: .monospaced))
                .scrollContentBackground(.hidden)
                .padding(8)
                .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 10, style: .continuous))

            HStack {
                Button("重新载入") {
                    model.reloadSettingsEditor()
                }
                Button("保存") {
                    model.saveSettingsEditor()
                }
                .keyboardShortcut("s", modifiers: [.command])
                Spacer()
            }
        }
        .padding(14)
        .onAppear { model.reloadSettingsEditor() }
        .onChange(of: model.settingsDoc) { _, _ in
            model.reloadSettingsEditor()
        }
    }
}
